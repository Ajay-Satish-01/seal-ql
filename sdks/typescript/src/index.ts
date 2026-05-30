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
  ServerError,
} from './errors.js';
export type {
  CatalogResponse,
  ChartType,
  ChartSpec,
  ChatRequest,
  ChatResponse,
  ChatStreamEvent,
  ChatStreamMeta,
  ColumnMetadata,
  SealOptions,
  DatabaseSchema,
  HealthResponse,
  QueryRequest,
  QueryResponse,
  SchemaColumn,
  SchemaTable,
} from './types.js';
