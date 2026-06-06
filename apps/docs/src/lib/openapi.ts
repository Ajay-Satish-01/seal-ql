import openapi from '@/data/openapi.json';
import {
  CHAT_METADATA_REFUSAL_EXAMPLE,
  CHAT_METADATA_SQL_EXAMPLE,
  QUERY_METADATA_EXAMPLE,
  chatStreamMetaExample,
} from '@/lib/execution-metadata';
import { VEGA_LITE_SCHEMA } from 'seal/constants';

export type OpenAPISpec = typeof openapi;

export const openApiSpec = openapi as OpenAPISpec;

export function getApiVersion(): string {
  return openApiSpec.info.version;
}

export function getApiTitle(): string {
  return openApiSpec.info.title;
}

interface PathMethod {
  path: string;
  method: string;
  summary?: string;
  description?: string;
  operationId?: string;
}

export function listEndpoints(): PathMethod[] {
  const endpoints: PathMethod[] = [];
  const paths = openApiSpec.paths as Record<
    string,
    Record<string, { summary?: string; description?: string; operationId?: string }>
  >;

  for (const [path, methods] of Object.entries(paths)) {
    for (const [method, details] of Object.entries(methods)) {
      if (['get', 'post', 'put', 'patch', 'delete'].includes(method)) {
        endpoints.push({
          path,
          method: method.toUpperCase(),
          summary: details.summary,
          description: details.description,
          operationId: details.operationId,
        });
      }
    }
  }
  return endpoints;
}

export function getSchema(name: string): Record<string, unknown> | undefined {
  const schemas = openApiSpec.components?.schemas as
    | Record<string, Record<string, unknown>>
    | undefined;
  return schemas?.[name];
}

export function schemaToExample(schemaName: string): string {
  const schema = getSchema(schemaName);
  if (!schema) return '{}';

  const examples: Record<string, unknown> = {
    QueryRequest: {
      query: 'Show total revenue by product category',
      database_id: 'default',
    },
    QueryResponse: {
      sql: 'SELECT category, SUM(amount) AS total_revenue FROM orders GROUP BY category LIMIT 10000',
      columns: [
        { name: 'category', type: 'varchar', nullable: true },
        { name: 'total_revenue', type: 'numeric', nullable: true },
      ],
      results: [{ category: 'Electronics', total_revenue: 45200.5 }],
      chart: {
        chart_type: 'bar',
        vega_lite_spec: {
          $schema: VEGA_LITE_SCHEMA,
          data: {
            values: [{ category: 'Electronics', total_revenue: 45200.5 }],
          },
          mark: { type: 'bar', tooltip: true },
          encoding: {
            x: { field: 'category', type: 'nominal' },
            y: { field: 'total_revenue', type: 'quantitative' },
          },
        },
        metadata: {
          requested_chart_type: 'bar',
          applied_chart_type: 'bar',
          x_field: 'category',
          y_field: 'total_revenue',
          color_field: null,
        },
      },
      metadata: QUERY_METADATA_EXAMPLE,
    },
    HealthResponse: { status: 'ok' },
    ChatRequest: {
      message: 'What tables are in the database?',
      session_id: null,
      include_charts: false,
      stream: false,
      enhancement: null,
      database_id: 'default',
    },
    ChatResponse: {
      session_id: '550e8400-e29b-41d4-a716-446655440000',
      message: 'The database includes products, orders, and events_hourly among others.',
      sources: ['products', 'orders'],
      sql: 'SELECT COUNT(*) AS n FROM orders',
      results: [{ n: 12840 }],
      columns: [{ name: 'n', type: 'int8', nullable: true }],
      chart: null,
      metadata: CHAT_METADATA_SQL_EXAMPLE,
    },
    ChatStreamMeta: chatStreamMetaExample(),
    ChatMetadata: CHAT_METADATA_SQL_EXAMPLE,
    ChatResponseRefusal: {
      session_id: '550e8400-e29b-41d4-a716-446655440001',
      message: 'I can only help with questions about your connected data and analytics.',
      sources: [],
      sql: null,
      results: null,
      columns: null,
      chart: null,
      metadata: CHAT_METADATA_REFUSAL_EXAMPLE,
    },
    QueryMetadata: QUERY_METADATA_EXAMPLE,
    CatalogResponse: {
      version: 1,
      generated_at: '2026-01-01T00:00:00Z',
      schema_hash: 'abc123',
      tables: [
        {
          name: 'orders',
          kind: 'table',
          table_description: 'Customer purchase transactions',
        },
      ],
    },
  };

  const example = examples[schemaName] ?? { note: `See ${schemaName} in OpenAPI components` };
  return JSON.stringify(example, null, 2);
}
