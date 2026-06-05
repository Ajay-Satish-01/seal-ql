/**
 * Docs-site execution metadata: re-exports shared contract + examples for static pages.
 */

export {
  type ChatMetadata,
  type ChatStreamMeta,
  type ColumnDescriptor,
  type EnhancementMetadata,
  type ExecutionMetadata,
  type ScopeMetadata,
  STREAM_META_METADATA_KEYS,
  chatResponseToStreamMeta,
  formatMetadataJson,
  hasMetadataContent,
} from '@seal/metadata-contract';

import {
  type ChatMetadata,
  type ChatStreamMeta,
  type ColumnDescriptor,
  type EnhancementMetadata,
  type ExecutionMetadata,
  type ScopeMetadata,
  formatMetadataJson,
} from '@seal/metadata-contract';

export interface MetadataFieldDef {
  name: string;
  description: string;
}

export const QUERY_EXECUTION_FIELDS: MetadataFieldDef[] = [
  { name: 'database_id', description: 'Routed backend (default "default")' },
  {
    name: 'row_count, execution_time_ms, truncated, warnings, repair_attempts',
    description: 'Execution stats and SQL boundary warnings (repair_attempts when trust enabled)',
  },
  { name: 'used_sql', description: 'Always true on successful query' },
  {
    name: 'tables_used, columns_used, catalog_matches, scope',
    description: 'SQL and catalog provenance when SEAL_TRUST_EXPLAINABILITY_ENABLED=true',
  },
  {
    name: 'sources (top-level)',
    description: 'Context tables selected for planning when trust explainability is enabled',
  },
];

export const CHAT_METADATA_EXTRA_FIELDS: MetadataFieldDef[] = [
  { name: 'metadata.enhancement.enabled', description: 'Whether the enhancement chain ran this turn' },
  {
    name: 'metadata.enhancement.applied',
    description: 'Enhancer names (e.g. schema_aware, vector_rag, multi_turn)',
  },
  {
    name: 'metadata.enhancement.vector_skipped_reason',
    description: 'non_default_database or vector_store_disabled when RAG cannot run',
  },
  {
    name: 'metadata.enhancement.unavailable_reason',
    description:
      'orchestrator_unavailable when the client requested enhancement (e.g. enhancement: true) but no orchestrator is configured — including guardrails refusals; omitted when an orchestrator exists but the turn is a refusal',
  },
  {
    name: 'metadata.scope',
    description:
      'ScopeMetadata: in_scope, reason, source (heuristic | llm | limits | disabled)',
  },
  {
    name: 'metadata.refusal',
    description: 'true on guardrails refusal (HTTP 200, no SQL)',
  },
  {
    name: 'metadata.suggested_queries',
    description:
      'Up to three example in-scope data questions on guardrails refusal (heuristic or refusal LLM)',
  },
  {
    name: 'metadata.sql_error',
    description: 'Data path failed; used_sql stays false and sql is omitted',
  },
];

export const SCOPE_IN_SCOPE: ScopeMetadata = {
  in_scope: true,
  reason: 'in_scope',
  source: 'heuristic',
};

export const SCOPE_OFF_TOPIC: ScopeMetadata = {
  in_scope: false,
  reason: 'off-topic',
  source: 'heuristic',
};

export const QUERY_METADATA_EXAMPLE: ExecutionMetadata = {
  database_id: 'default',
  row_count: 4,
  execution_time_ms: 24.5,
  truncated: false,
  warnings: [],
  repair_attempts: 0,
  used_sql: true,
  tables_used: ['orders'],
  columns_used: ['orders.id'],
  catalog_matches: [{ name: 'orders', schema: 'public', description: 'Customer orders' }],
};

export const CHAT_METADATA_SQL_EXAMPLE: ChatMetadata = {
  ...QUERY_METADATA_EXAMPLE,
  enhancement: {
    enabled: true,
    applied: ['schema_aware', 'vector_rag'],
  },
  scope: SCOPE_IN_SCOPE,
};

export const CHAT_METADATA_REFUSAL_EXAMPLE: ChatMetadata = {
  database_id: 'default',
  row_count: 0,
  execution_time_ms: 0,
  truncated: false,
  warnings: [],
  repair_attempts: 0,
  used_sql: false,
  enhancement: {
    enabled: false,
    applied: [],
  },
  scope: SCOPE_OFF_TOPIC,
  refusal: true,
  suggested_queries: ['Show order count by month', 'What tables are available?'],
};

const DEMO_SESSION_ID = 'demo-session-a1b2c3d4';

export const QUERY_METADATA_JSON = formatMetadataJson({ metadata: QUERY_METADATA_EXAMPLE });
export const CHAT_METADATA_SQL_JSON = formatMetadataJson({ metadata: CHAT_METADATA_SQL_EXAMPLE });
export const CHAT_METADATA_REFUSAL_JSON = formatMetadataJson({
  metadata: CHAT_METADATA_REFUSAL_EXAMPLE,
});

export function chatStreamMetaExample(overrides?: {
  session_id?: string;
  sql?: string | null;
  results?: Record<string, unknown>[] | null;
  columns?: ColumnDescriptor[] | null;
}): ChatStreamMeta {
  return {
    session_id: overrides?.session_id ?? DEMO_SESSION_ID,
    sources: ['orders', 'products'],
    sql: overrides?.sql ?? 'SELECT COUNT(*) AS n FROM orders',
    results: overrides?.results ?? [{ n: 42 }],
    columns: overrides?.columns ?? [{ name: 'n', type: 'int8', nullable: true }],
    chart: null,
    scope: CHAT_METADATA_SQL_EXAMPLE.scope,
    ...QUERY_METADATA_EXAMPLE,
    row_count: overrides?.results?.length ?? 1,
    enhancement: CHAT_METADATA_SQL_EXAMPLE.enhancement,
  };
}

export const CHAT_STREAM_META_JSON = formatMetadataJson(chatStreamMetaExample());

export function buildDemoChatMetadata(
  queryMeta: Pick<
    ExecutionMetadata,
    'row_count' | 'execution_time_ms' | 'truncated' | 'warnings' | 'repair_attempts'
  >,
  enhancement: EnhancementMetadata = { enabled: true, applied: ['schema_aware', 'multi_turn'] },
): ChatMetadata {
  return {
    database_id: 'default',
    row_count: queryMeta.row_count,
    execution_time_ms: queryMeta.execution_time_ms,
    truncated: queryMeta.truncated,
    warnings: queryMeta.warnings ?? [],
    repair_attempts: queryMeta.repair_attempts ?? 0,
    used_sql: true,
    tables_used: QUERY_METADATA_EXAMPLE.tables_used,
    columns_used: QUERY_METADATA_EXAMPLE.columns_used,
    catalog_matches: QUERY_METADATA_EXAMPLE.catalog_matches,
    enhancement,
    scope: SCOPE_IN_SCOPE,
  };
}
