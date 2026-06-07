/**
 * Seal TypeScript SDK
 *
 * @example
 * ```ts
 * import { Seal } from "seal";
 *
 * const client = new Seal({ baseUrl: "http://localhost:8000" });
 * const result = await client.query("Show me monthly revenue");
 * console.log(result.sql);
 * ```
 */

export { Seal } from './client.js';
export { VegaChart, type VegaChartProps } from './react.js';
export {
  parseSseEventBlock,
  splitSseBuffer,
  flushSseRemainder,
  type SseParseResult,
} from './sse.js';
export {
  SealError,
  SealConnectionError,
  ConnectionError,
  QueryError,
  QueryOutOfScopeError,
  ServerError,
} from './errors.js';
export { VEGA_LITE_SCHEMA } from './constants.js';
export type {
  CatalogResponse,
  ChartType,
  ChartSpec,
  ChatMetadata,
  ChatRequest,
  ChatResponse,
  ChatStreamEvent,
  ChatStreamMeta,
  ColumnMetadata,
  EnhancementInfo,
  EnhancementMetadata,
  ReasoningInfo,
  ReasoningMetadata,
  SealOptions,
  DatabaseSchema,
  HealthResponse,
  QueryMetadata,
  QueryRequest,
  QueryResponse,
  QueryOutOfScopeDetail,
  QueryOutOfScopeErrorResponse,
  SchemaColumn,
  SchemaTable,
  TableSchema,
} from './types.js';
