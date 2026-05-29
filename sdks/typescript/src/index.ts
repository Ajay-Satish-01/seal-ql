/**
 * Intelligence Connector TypeScript SDK
 *
 * @example
 * ```ts
 * import { IntelligenceConnector } from "intelligence-sdk";
 *
 * const client = new IntelligenceConnector({ baseUrl: "http://localhost:8000" });
 * const result = await client.query("Show me monthly revenue");
 * console.log(result.sql);
 * ```
 */

export { IntelligenceConnector } from './client.js';
export { VegaChart, type VegaChartProps } from './react.js';
export { IntelligenceConnectorError, ConnectionError, QueryError, ServerError } from './errors.js';
export type {
  ChartType,
  ChartSpec,
  ColumnMetadata,
  ConnectorOptions,
  DatabaseSchema,
  HealthResponse,
  QueryRequest,
  QueryResponse,
  SchemaColumn,
  SchemaTable,
} from './types.js';
