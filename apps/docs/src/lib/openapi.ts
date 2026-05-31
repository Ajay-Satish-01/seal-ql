import openapi from '@/data/openapi.json';

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
          $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
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
      metadata: {
        row_count: 1,
        execution_time_ms: 24.5,
        truncated: false,
        warnings: [],
      },
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
      sql: null,
      results: null,
      columns: null,
      chart: null,
      metadata: { used_sql: false, enhancement: { applied: ['schema_aware', 'multi_turn'] } },
    },
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
