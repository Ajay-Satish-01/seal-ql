/**
 * TypeScript types for the Seal API.
 *
 * These mirror the Pydantic models on the server side,
 * keeping the SDK fully decoupled from server internals.
 */

// ============================================================
// Enums
// ============================================================

export type ChartType = 'bar' | 'line' | 'pie' | 'scatter' | 'area' | 'table' | 'metric_card';

// ============================================================
// Response Types
// ============================================================

export interface ColumnMetadata {
  name: string;
  type: string;
  nullable?: boolean;
}

export interface ChartSpec {
  chart_type: ChartType;
  vega_lite_spec: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface QueryResponse {
  sql: string;
  columns: ColumnMetadata[];
  results: Record<string, unknown>[];
  chart: ChartSpec | null;
  metadata: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
}

export interface SchemaColumn {
  name: string;
  type: string;
  nullable?: boolean;
}

export interface SchemaTable {
  name: string;
  columns: SchemaColumn[];
  kind?: string;
}

export interface DatabaseSchema {
  dialect: string;
  tables: SchemaTable[];
}

// ============================================================
// Request Types
// ============================================================

export interface QueryRequest {
  query: string;
  database_id?: string;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  include_charts?: boolean;
  stream?: boolean;
  enhancement?: boolean;
  database_id?: string;
}

export interface ChatResponse {
  session_id: string;
  message: string;
  sources?: string[];
  sql?: string | null;
  results?: Record<string, unknown>[] | null;
  columns?: ColumnMetadata[] | null;
  chart?: ChartSpec | null;
  metadata?: Record<string, unknown>;
}

export interface CatalogResponse {
  version: number;
  generated_at?: string | null;
  schema_hash?: string | null;
  tables: Record<string, unknown>[];
}

/** Payload on SSE `seal.meta` before streamed answer tokens. */
export interface ChatStreamMeta {
  session_id: string;
  sources?: string[];
  sql?: string | null;
  chart?: ChartSpec | null;
  enhancement?: Record<string, unknown>;
}

export type ChatStreamEvent =
  | { type: 'meta'; data: ChatStreamMeta }
  | { type: 'delta'; content: string }
  | { type: 'done' };

// ============================================================
// Client Options
// ============================================================

export interface SealOptions {
  /** Base URL of the Seal API (e.g., "http://localhost:8000"). */
  baseUrl: string;
  /** API key sent as the `X-API-Key` header when the server has `SEAL_API_KEY` set. */
  apiKey?: string;
  /** Request timeout in milliseconds (default: 120000). */
  timeout?: number;
  /** Extra headers to include in every request. */
  headers?: Record<string, string>;
}
