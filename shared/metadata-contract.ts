/**
 * Shared execution metadata types and seal.meta flattening.
 * Used by apps/docs, apps/web, and scripts/verify_chat_flatten_contract.ts.
 * STREAM_META_METADATA_KEYS is sourced from config/stream_meta_metadata_keys.json.
 */

import streamMetaMetadataKeys from '../config/stream_meta_metadata_keys.json';

export interface ColumnDescriptor {
  name: string;
  type: string;
  nullable?: boolean;
}

export type VectorSkippedReason = 'non_default_database' | 'vector_store_disabled';
export type EnhancementUnavailableReason = 'orchestrator_unavailable';
export type ScopeSource = 'heuristic' | 'llm' | 'limits' | 'disabled';

export interface EnhancementMetadata {
  enabled: boolean;
  applied: string[];
  vector_skipped_reason?: VectorSkippedReason | null;
  unavailable_reason?: EnhancementUnavailableReason | null;
}

export interface ScopeMetadata {
  in_scope: boolean;
  reason?: string | null;
  source: ScopeSource;
}

export interface CatalogMatchItem {
  name: string;
  schema?: string;
  description?: string | null;
}

/** Shared execution fields on query and chat. */
export interface ExecutionMetadata {
  database_id?: string;
  row_count?: number;
  execution_time_ms?: number;
  truncated?: boolean;
  warnings?: string[];
  repair_attempts?: number;
  used_sql?: boolean;
  tables_used?: string[];
  columns_used?: string[];
  catalog_matches?: CatalogMatchItem[];
  enhancement?: EnhancementMetadata;
}

export interface ChatMetadata extends ExecutionMetadata {
  scope?: ScopeMetadata;
  refusal?: boolean;
  sql_error?: boolean;
  /** Up to three example in-scope questions on guardrails refusal. */
  suggested_queries?: string[];
}

/** Flat `seal.meta` SSE payload (execution fields at top level, not under metadata). */
export interface ChatStreamMeta extends ExecutionMetadata {
  session_id: string;
  sources?: string[] | null;
  sql?: string | null;
  results?: Record<string, unknown>[] | null;
  columns?: ColumnDescriptor[] | null;
  chart?: Record<string, unknown> | null;
  scope?: ScopeMetadata;
  refusal?: boolean;
  sql_error?: boolean;
  suggested_queries?: string[];
}

/** Keys copied from chat JSON `metadata` onto flat seal.meta (sync with Python). */
export const STREAM_META_METADATA_KEYS = streamMetaMetadataKeys as readonly string[];

export function formatMetadataJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

export function hasMetadataContent(metadata: ChatMetadata | ExecutionMetadata | undefined): boolean {
  return metadata != null && Object.keys(metadata).length > 0;
}

/**
 * Flatten ChatResponse JSON into seal.meta shape.
 * Keep in sync with `chat_response_to_stream_meta` in validate_metadata.py.
 */
export function chatResponseToStreamMeta(response: {
  session_id: string;
  sources?: string[];
  sql?: string | null;
  results?: ReadonlyArray<Record<string, unknown>> | null;
  columns?: ReadonlyArray<ColumnDescriptor> | null;
  chart?: Record<string, unknown> | null;
  metadata?: ChatMetadata;
}): ChatStreamMeta {
  const meta = response.metadata ?? {};
  const event: Record<string, unknown> = {
    session_id: response.session_id,
    sources: response.sources ?? null,
    sql: response.sql ?? null,
    results: response.results ?? null,
    columns: response.columns ?? null,
    chart: response.chart ?? null,
  };
  const metaRecord = meta as Record<string, unknown>;
  for (const key of STREAM_META_METADATA_KEYS) {
    const value = metaRecord[key];
    if (key in metaRecord && value !== undefined && value !== null) {
      event[key] = value;
    }
  }
  return event as unknown as ChatStreamMeta;
}
