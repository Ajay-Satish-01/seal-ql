/**
 * Shared client-side validation for SSE `seal.meta` payloads.
 * Used by apps/docs and apps/web — keep rules aligned with
 * `seal_core.pipeline.validate_metadata.validate_stream_meta_event`.
 */

import type {
  EnhancementUnavailableReason,
  ScopeMetadata,
  ScopeSource,
  VectorSkippedReason,
} from './metadata-contract';

const SCOPE_SOURCES: readonly ScopeSource[] = ['heuristic', 'llm', 'limits', 'disabled'];
const VECTOR_SKIPPED_REASONS: readonly VectorSkippedReason[] = [
  'non_default_database',
  'vector_store_disabled',
];
const UNAVAILABLE_REASONS: readonly EnhancementUnavailableReason[] = ['orchestrator_unavailable'];

function isScopeSource(value: string): value is ScopeSource {
  return (SCOPE_SOURCES as readonly string[]).includes(value);
}

function isVectorSkippedReason(value: string): value is VectorSkippedReason {
  return (VECTOR_SKIPPED_REASONS as readonly string[]).includes(value);
}

function isUnavailableReason(value: string): value is EnhancementUnavailableReason {
  return (UNAVAILABLE_REASONS as readonly string[]).includes(value);
}

export interface StreamMetaPayload {
  session_id: string;
  sources?: string[] | null;
  sql?: string | null;
  results?: Record<string, unknown>[] | null;
  columns?: Array<{ name: string; type: string; nullable?: boolean }> | null;
  chart?: Record<string, unknown> | null;
  database_id?: string;
  row_count?: number;
  execution_time_ms?: number;
  truncated?: boolean;
  warnings?: string[];
  repair_attempts?: number;
  used_sql?: boolean;
  enhancement?: {
    enabled: boolean;
    applied: string[];
    vector_skipped_reason?: VectorSkippedReason | null;
    unavailable_reason?: EnhancementUnavailableReason | null;
  };
  scope?: ScopeMetadata;
  refusal?: boolean;
  sql_error?: boolean;
}

/** Light runtime checks before treating an SSE meta payload as StreamMetaPayload. */
export function parseStreamMeta(data: unknown): StreamMetaPayload {
  if (data == null || typeof data !== 'object') {
    throw new Error('seal.meta payload must be an object');
  }
  const record = data as Record<string, unknown>;
  const sessionId = record.session_id;
  if (typeof sessionId !== 'string' || !sessionId.trim()) {
    throw new Error('seal.meta missing session_id');
  }

  for (const key of ['used_sql', 'refusal', 'sql_error', 'truncated'] as const) {
    if (key in record && typeof record[key] !== 'boolean') {
      throw new Error(`seal.meta ${key} must be a boolean`);
    }
  }

  const sql = record.sql;
  const sqlPresent = typeof sql === 'string' && sql.trim().length > 0;
  if (sqlPresent) {
    for (const key of [
      'database_id',
      'row_count',
      'execution_time_ms',
      'truncated',
      'warnings',
      'repair_attempts',
      'used_sql',
    ] as const) {
      if (!(key in record)) {
        throw new Error(`seal.meta missing ${key} when sql is present`);
      }
    }
  }

  const needsEnhancement =
    record.used_sql === true || record.refusal === true || record.sql_error === true;
  if (needsEnhancement && readEnhancement(record.enhancement) === undefined) {
    throw new Error('seal.meta invalid enhancement object');
  }
  if ('scope' in record && readScope(record.scope) === undefined) {
    throw new Error('seal.meta invalid scope object');
  }

  const columns = record.columns;
  if (columns != null) {
    if (!Array.isArray(columns)) {
      throw new Error('seal.meta columns must be an array or null');
    }
    for (const col of columns) {
      if (
        col == null ||
        typeof col !== 'object' ||
        typeof (col as Record<string, unknown>).name !== 'string' ||
        typeof (col as Record<string, unknown>).type !== 'string'
      ) {
        throw new Error('seal.meta columns entries must have name and type');
      }
    }
  }

  return record as unknown as StreamMetaPayload;
}

export type ParseStreamMetaResult =
  | { ok: true; data: StreamMetaPayload }
  | { ok: false; error: string };

/** Non-throwing wrapper for SSE consumers that should continue on bad meta. */
export function tryParseStreamMeta(data: unknown): ParseStreamMetaResult {
  try {
    return { ok: true, data: parseStreamMeta(data) };
  } catch (e) {
    const message = e instanceof Error ? e.message : 'Invalid seal.meta payload';
    return { ok: false, error: message };
  }
}

function readEnhancement(raw: unknown): StreamMetaPayload['enhancement'] | undefined {
  if (raw == null || typeof raw !== 'object') {
    return undefined;
  }
  const enh = raw as Record<string, unknown>;
  if (typeof enh.enabled !== 'boolean' || !Array.isArray(enh.applied)) {
    return undefined;
  }
  if (!enh.applied.every((item) => typeof item === 'string')) {
    return undefined;
  }
  if (
    enh.vector_skipped_reason !== undefined &&
    enh.vector_skipped_reason !== null &&
    (typeof enh.vector_skipped_reason !== 'string' ||
      !isVectorSkippedReason(enh.vector_skipped_reason))
  ) {
    return undefined;
  }
  if (
    enh.unavailable_reason !== undefined &&
    enh.unavailable_reason !== null &&
    (typeof enh.unavailable_reason !== 'string' || !isUnavailableReason(enh.unavailable_reason))
  ) {
    return undefined;
  }
  const vectorSkipped =
    typeof enh.vector_skipped_reason === 'string' &&
    isVectorSkippedReason(enh.vector_skipped_reason)
      ? enh.vector_skipped_reason
      : null;
  const unavailable =
    typeof enh.unavailable_reason === 'string' && isUnavailableReason(enh.unavailable_reason)
      ? enh.unavailable_reason
      : null;
  return {
    enabled: enh.enabled,
    applied: enh.applied as string[],
    vector_skipped_reason: vectorSkipped,
    unavailable_reason: unavailable,
  };
}

function readScope(raw: unknown): StreamMetaPayload['scope'] | undefined {
  if (raw == null || typeof raw !== 'object') {
    return undefined;
  }
  const scope = raw as Record<string, unknown>;
  if (
    typeof scope.in_scope === 'boolean' &&
    typeof scope.reason === 'string' &&
    typeof scope.source === 'string' &&
    isScopeSource(scope.source)
  ) {
    return {
      in_scope: scope.in_scope,
      reason: scope.reason,
      source: scope.source,
    };
  }
  return undefined;
}

/**
 * Best-effort fields from a malformed seal.meta payload (e.g. missing enhancement).
 * Lets UIs keep session/database continuity when strict client checks fail.
 */
export function partialStreamMetaFromRaw(data: unknown): Partial<StreamMetaPayload> {
  if (data == null || typeof data !== 'object') {
    return {};
  }
  const record = data as Record<string, unknown>;
  const partial: Partial<StreamMetaPayload> = {};

  const sessionId = record.session_id;
  if (typeof sessionId === 'string' && sessionId.trim()) {
    partial.session_id = sessionId;
  }
  if (typeof record.database_id === 'string') {
    partial.database_id = record.database_id;
  }
  const sources = record.sources;
  if (Array.isArray(sources) && sources.every((s) => typeof s === 'string')) {
    partial.sources = sources;
  }
  if (typeof record.sql === 'string') {
    partial.sql = record.sql;
  }
  if (record.refusal === true) {
    partial.refusal = true;
  }
  if (record.sql_error === true) {
    partial.sql_error = true;
  }
  if (typeof record.used_sql === 'boolean') {
    partial.used_sql = record.used_sql;
  }
  if (typeof record.row_count === 'number') {
    partial.row_count = record.row_count;
  }
  if (typeof record.execution_time_ms === 'number') {
    partial.execution_time_ms = record.execution_time_ms;
  }
  if (typeof record.truncated === 'boolean') {
    partial.truncated = record.truncated;
  }
  if (Array.isArray(record.warnings) && record.warnings.every((w) => typeof w === 'string')) {
    partial.warnings = record.warnings;
  }
  if (typeof record.repair_attempts === 'number') {
    partial.repair_attempts = record.repair_attempts;
  }

  const enhancement = readEnhancement(record.enhancement);
  if (enhancement) {
    partial.enhancement = enhancement;
  }
  const scope = readScope(record.scope);
  if (scope) {
    partial.scope = scope;
  }

  return partial;
}
