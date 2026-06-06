/**
 * Public SDK types — generated from the FastAPI OpenAPI spec (Pydantic v2 models).
 *
 * Regenerate after API schema changes:
 *   make openapi && cd sdks/typescript && pnpm run generate:api-types
 *
 * Runtime SSE validation uses vendored copies of `shared/stream-meta.ts` (see prebuild).
 */

import type { components } from './generated/openapi.js';

type Schemas = components['schemas'];

export { VEGA_LITE_SCHEMA } from './constants.js';

/** API chart type enum from OpenAPI. */
export type ChartType = Schemas['ChartType'];

export type ChartSpec = Schemas['ChartSpec'];
export type ColumnMetadata = Schemas['ColumnMetadata'];
export type QueryMetadata = Schemas['QueryMetadata'];
export type QueryRequest = Schemas['QueryRequest'];
export type QueryResponse = Schemas['QueryResponse'];
/** Guardrails rejection body nested under FastAPI ``detail`` on ``POST /v1/query`` 400. */
export type QueryOutOfScopeDetail = Schemas['QueryOutOfScopeDetail'];
export type QueryOutOfScopeErrorResponse = Schemas['QueryOutOfScopeErrorResponse'];

/** OpenAPI name `EnhancementInfo` — same shape as core `EnhancementMetadata`. */
export type EnhancementMetadata = Schemas['EnhancementInfo'];
export type EnhancementInfo = Schemas['EnhancementInfo'];

export type ChatMetadata = Schemas['ChatMetadata'];
export type ChatRequest = Schemas['ChatRequest'];
export type ChatResponse = Schemas['ChatResponse'];
export type ChatStreamMeta = Schemas['ChatStreamMeta'];

export type HealthResponse = Schemas['HealthResponse'];
export type CatalogResponse = Schemas['CatalogResponse'];
export type DatabaseSchema = Schemas['DatabaseSchema'];
export type TableSchema = Schemas['TableSchema'];

/** Convenience aliases for schema introspection columns. */
export type SchemaTable = Pick<TableSchema, 'name' | 'columns'> & {
  kind?: TableSchema['kind'];
};
export type SchemaColumn = NonNullable<TableSchema['columns']>[number];

/** SDK-only: streamed chat events (includes client-side meta_error). */
export type ChatStreamEvent =
  | { type: 'meta'; data: ChatStreamMeta }
  | { type: 'meta_error'; error: string; partial: Partial<ChatStreamMeta> }
  | { type: 'delta'; content: string }
  | { type: 'done' };

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
