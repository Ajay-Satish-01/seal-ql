import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { EndpointBlock } from '@/components/docs/endpoint-block';
import { ParamTable } from '@/components/docs/param-table';
import { Callout } from '@/components/docs/callout';
import Link from 'next/link';
import { listEndpoints, schemaToExample, getApiVersion } from '@/lib/openapi';
import { SITE } from '@/lib/constants';

export default function ApiReferencePage() {
  const version = getApiVersion();
  const endpoints = listEndpoints();

  const health = endpoints.find((e) => e.path === '/health');
  const schema = endpoints.find((e) => e.path === '/v1/schema');
  const query = endpoints.find((e) => e.path === '/v1/query');

  return (
    <div className="max-w-3xl">
      <PageHeader
        title="API Reference"
        description={`REST API v${version} — generated from the committed OpenAPI spec.`}
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <Callout variant="info" title="Try it on your stack">
          After <Link href="/docs/self-hosting">running the Docker image</Link>, open{' '}
          <code>{'{baseUrl}'}/docs</code> for Swagger UI against your live API, or download{' '}
          <a href="/openapi.json" className="text-primary">
            openapi.json
          </a>{' '}
          from this site.
        </Callout>

        {health ? (
          <EndpointBlock
            method={health.method}
            path={health.path}
            summary={health.summary}
            description={health.description}
          >
            <h4 className="text-foreground mb-2 text-sm font-semibold">Response</h4>
            <CodeBlock language="json" code={schemaToExample('HealthResponse')} />
          </EndpointBlock>
        ) : null}

        {schema ? (
          <EndpointBlock
            method={schema.method}
            path={schema.path}
            summary={schema.summary}
            description={schema.description}
          >
            <p>
              Returns full database introspection (tables, columns, relationships, TimescaleDB
              metadata).
            </p>
          </EndpointBlock>
        ) : null}

        {query ? (
          <EndpointBlock
            method={query.method}
            path={query.path}
            summary={query.summary}
            description={query.description}
          >
            <ParamTable
              title="Request body"
              rows={[
                {
                  name: 'query',
                  type: 'string',
                  required: true,
                  description: 'Natural language question.',
                },
                {
                  name: 'database_id',
                  type: 'string',
                  required: false,
                  description: 'Target database id (default: "default").',
                },
              ]}
            />
            <CodeBlock language="json" code={schemaToExample('QueryRequest')} />
            <h4 className="text-foreground mt-8 mb-2 text-sm font-semibold">Response</h4>
            <ParamTable
              rows={[
                { name: 'sql', type: 'string', description: 'Validated SQL that was executed.' },
                {
                  name: 'columns',
                  type: 'ColumnMetadata[]',
                  description: 'Column name, DB type, nullable.',
                },
                { name: 'results', type: 'object[]', description: 'Result rows.' },
                {
                  name: 'chart',
                  type: 'ChartSpec | null',
                  description: 'chart_type, vega_lite_spec, metadata.',
                },
                {
                  name: 'metadata',
                  type: 'object',
                  description: 'row_count, execution_time_ms, truncated, warnings.',
                },
              ]}
            />
            <CodeBlock language="json" code={schemaToExample('QueryResponse')} />
          </EndpointBlock>
        ) : null}

        <h2 className="text-foreground mt-10 text-2xl font-bold">Errors</h2>
        <p>HTTP errors return FastAPI-style JSON:</p>
        <CodeBlock language="json" code={'{\n  "detail": "Query failed: ..."\n}'} />

        <p className="mt-8">
          Source repository:{' '}
          <a href={SITE.github} className="text-primary" target="_blank" rel="noreferrer">
            GitHub
          </a>
        </p>
      </div>
    </div>
  );
}
