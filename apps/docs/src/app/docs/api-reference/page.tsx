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
  const chat = endpoints.find((e) => e.path === '/v1/chat');
  const catalog = endpoints.find((e) => e.path === '/v1/catalog');

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
              metadata) for a registered <code>database_id</code>.
            </p>
            <p>
              Query parameter <code>database_id</code> (default <code>&quot;default&quot;</code>).
              See <Link href="/docs/multi-database">Multi-database routing</Link>.
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
                  description:
                    'Registered database id (default: "default"). Resolved before guardrails; unknown id → HTTP 404.',
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
                  type: 'QueryMetadata',
                  description:
                    'ExecutionMetadata: database_id, row_count, execution_time_ms, truncated, warnings, repair_attempts, used_sql.',
                },
              ]}
            />
            <CodeBlock language="json" code={schemaToExample('QueryResponse')} />
            <h4 className="text-foreground mt-8 mb-2 text-sm font-semibold">Errors</h4>
            <ul className="text-muted-foreground list-disc space-y-2 pl-5 text-sm">
              <li>
                <strong>400</strong> — guardrails out of scope: structured{' '}
                <code>detail</code> with <code>query_out_of_scope</code>, <code>reason</code>,{' '}
                <code>suggested_queries</code> (OpenAPI <code>QueryOutOfScopeErrorResponse</code>).
                SDKs raise <code>QueryOutOfScopeError</code>.
              </li>
              <li>
                <strong>404</strong> — unknown <code>database_id</code>
              </li>
              <li>
                <strong>422</strong> — request body over Pydantic <code>max_length</code> (before
                guardrails limits)
              </li>
              <li>
                <strong>502</strong> — LiteLLM provider failure (auth, model not found, bad request)
              </li>
              <li>
                <strong>503</strong> — LiteLLM rate limit exceeded
              </li>
            </ul>
          </EndpointBlock>
        ) : null}

        {catalog ? (
          <EndpointBlock
            method={catalog.method}
            path={catalog.path}
            summary={catalog.summary}
            description={catalog.description}
          >
            <p>
              Global auto-generated data catalog (business descriptions). Used by chat and query
              planners. See <Link href="/docs/data-catalog">Data catalog</Link>.
            </p>
            <h4 className="text-foreground mt-6 mb-2 text-sm font-semibold">Response</h4>
            <CodeBlock language="json" code={schemaToExample('CatalogResponse')} />
          </EndpointBlock>
        ) : null}

        {chat ? (
          <EndpointBlock
            method={chat.method}
            path={chat.path}
            summary={chat.summary}
            description={chat.description}
          >
            <ParamTable
              title="Request body"
              rows={[
                { name: 'message', type: 'string', required: true, description: 'User message.' },
                {
                  name: 'session_id',
                  type: 'string',
                  required: false,
                  description: 'Conversation session for follow-ups.',
                },
                {
                  name: 'database_id',
                  type: 'string',
                  required: false,
                  description:
                    'Registered database id (default: "default"). Must match pinned session on follow-ups or HTTP 400 session_database_id_mismatch.',
                },
                {
                  name: 'include_charts',
                  type: 'boolean',
                  required: false,
                  description: 'Attach Vega-Lite chart when SQL runs.',
                },
                {
                  name: 'stream',
                  type: 'boolean',
                  required: false,
                  description: 'SSE stream for final answer.',
                },
                {
                  name: 'enhancement',
                  type: 'boolean',
                  required: false,
                  description: 'Override CHAT_ENHANCEMENT_ENABLED.',
                },
              ]}
            />
            <CodeBlock language="json" code={schemaToExample('ChatRequest')} />
            <h4 className="text-foreground mt-6 mb-2 text-sm font-semibold">Response (JSON)</h4>
            <CodeBlock language="json" code={schemaToExample('ChatResponse')} />
            <p className="mt-4">
              JSON responses use <code>ChatMetadata</code> (nested <code>metadata</code> with{' '}
              <code>ScopeMetadata</code>, <code>EnhancementInfo</code>, optional{' '}
              <code>suggested_queries</code> on guardrails refusal). Streaming uses flat{' '}
              <code>ChatStreamMeta</code> on <code>seal.meta</code> — see{' '}
              <Link href="/docs/execution-metadata">Execution metadata</Link>.
            </p>
            <h4 className="text-foreground mt-6 mb-2 text-sm font-semibold">Errors</h4>
            <ul className="text-muted-foreground list-disc space-y-2 pl-5 text-sm">
              <li>
                <strong>200</strong> — out-of-scope message: <code>metadata.refusal=true</code> and{' '}
                <code>metadata.suggested_queries</code> (no SQL)
              </li>
              <li>
                <strong>400</strong> — <code>system</code> role in <code>messages</code>, session{' '}
                <code>database_id</code> mismatch, or history over limit
              </li>
              <li>
                <strong>502</strong> — LiteLLM provider failure (auth, model not found, bad request)
              </li>
              <li>
                <strong>503</strong> — LiteLLM rate limit exceeded
              </li>
            </ul>
            <p className="mt-2">
              Examples: <Link href="/docs/chat-qa">Chat & Q&A</Link>,{' '}
              <Link href="/docs/chat-streaming">Streaming</Link>.
            </p>
          </EndpointBlock>
        ) : null}

        <h2 className="text-foreground mt-10 text-2xl font-bold">Workspace &amp; vector</h2>
        <p>
          Full guide: <Link href="/docs/workspace">Workspace settings</Link>. Include the{' '}
          <code>X-API-Key</code> header on all <code>/v1/*</code> routes.
        </p>
        <EndpointBlock
          method="GET"
          path="/v1/workspace/settings"
          summary="Effective workspace settings"
          description="Returns settings, field schema, storage metadata (postgres vs file), and pending_apply / restart_required."
        />
        <EndpointBlock
          method="PATCH"
          path="/v1/workspace/settings"
          summary="Update workspace settings"
          description="Body: { settings: { ... } }. Dev mode applies hot-reload keys immediately; prod may require POST .../apply."
        />
        <EndpointBlock
          method="POST"
          path="/v1/workspace/settings/apply"
          summary="Apply persisted hot-reload settings"
          description="Production: apply keys saved via PATCH that support in-process reload (guardrails, limits)."
        />
        <EndpointBlock
          method="PATCH"
          path="/v1/catalog/descriptions"
          summary="Persist catalog description overrides"
          description="Table/view descriptions stored in workspace; reapplied after POST /v1/catalog/sync."
        />
        <EndpointBlock
          method="POST"
          path="/v1/vector/reindex"
          summary="Rebuild vector index"
          description="Requires VECTOR_STORE=chroma and SEAL_EXTRA=chroma build. Indexes schema + catalog text."
        />

        <h2 className="text-foreground mt-10 text-2xl font-bold">Errors</h2>
        <p>HTTP errors return FastAPI-style JSON:</p>
        <CodeBlock language="json" code={'{\n  "detail": "Query failed: ..."\n}'} />
        <ul className="text-muted-foreground mt-4 list-disc space-y-2 pl-5 text-sm">
          <li>
            <strong>401</strong> — missing or invalid <code>X-API-Key</code> on <code>/v1/*</code>
          </li>
          <li>
            <strong>502</strong> — LiteLLM failures on <code>/v1/query</code>,{' '}
            <code>/v1/chat</code>, or <code>/v1/vector/reindex</code> (auth, model, provider error)
          </li>
          <li>
            <strong>503</strong> — LiteLLM rate limit; rare <code>503</code> if auth is misconfigured
            at runtime
          </li>
        </ul>

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
