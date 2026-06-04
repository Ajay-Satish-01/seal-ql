import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { DocsProse } from '@/components/docs/docs-prose';
import { Callout } from '@/components/docs/callout';
import { DocLink } from '@/components/docs/doc-link';

export default function FeaturesPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Features"
        description="Everything Seal provides for production NL analytics — from introspection to charts."
      />

      <DocsProse>
        <p>
          Seal is a single API gateway and SDK surface. The sections below map to packages in{' '}
          <code>packages/core</code>, routes under <code>/v1/*</code>, and the operational dashboard
          on port <strong>3001</strong>.
        </p>

        <h2 id="introspection">Schema introspection</h2>
        <p>
          Before any SQL is generated, Seal reads live DDL from your database and builds a structured
          schema model (tables, columns, types, foreign keys, TimescaleDB hypertables and continuous
          aggregates).
        </p>
        <ul>
          <li>
            <strong>Dialects:</strong> Postgres, TimescaleDB, DuckDB
          </li>
          <li>
            <strong>API:</strong> <code>GET /v1/schema</code> · SDK <code>client.schema()</code>
          </li>
          <li>
            <strong>Token efficiency:</strong> enhancement and planners inject relevant tables only
          </li>
        </ul>

        <h2 id="catalog">Data catalog</h2>
        <p>
          A global <code>config/catalog.yaml</code> is auto-generated from introspection (
          <code>CATALOG_AUTO_SYNC</code>). You add human-readable{' '}
          <code>table_description</code> / <code>view_description</code> fields — used by{' '}
          <code>/v1/query</code>, <code>/v1/chat</code>, and vector indexing.
        </p>
        <ul>
          <li>
            <code>GET /v1/catalog</code> · <code>POST /v1/catalog/sync</code> ·{' '}
            <code>PATCH /v1/catalog/descriptions</code>
          </li>
          <li>
            Dashboard and workspace DB persist descriptions across sync — see{' '}
            <Link href="/docs/data-catalog">Data catalog</Link>
          </li>
        </ul>

        <h2 id="planner">Query planner &amp; auto-repair</h2>
        <p>
          The planner uses <strong>LiteLLM</strong> + <strong>Instructor</strong> to produce structured
          SQL plans (not free-text). If execution fails (unknown column, syntax error), the error is
          fed back and the agent retries within configured limits — transparent to the caller.
        </p>
        <ul>
          <li>
            <code>POST /v1/query</code> — always returns SQL, rows, metadata, and a Vega-Lite chart
          </li>
          <li>Shared execution path with chat when a turn runs SQL</li>
        </ul>

        <h2 id="sql-safety">Zero-trust SQL (SQLGlot)</h2>
        <p>
          Every generated statement is parsed to an AST before execution — validator, sanitizer, then
          executor. Full reference: <Link href="/docs/zero-trust-sql">Zero-trust SQL boundary</Link>.
        </p>
        <ul>
          <li>Schema validation (tables, columns, ambiguous unqualified names)</li>
          <li>
            Blocks DML/DDL, <code>COPY</code>, <code>SELECT INTO</code>, locking clauses, and admin
            statements
          </li>
          <li>Rejects dynamic <code>LIMIT</code>; injects/clamps outer <code>LIMIT</code></li>
          <li>Dialect-aware (<code>postgres</code> / <code>duckdb</code>) in <code>packages/sql</code></li>
        </ul>

        <h2 id="embedding">Embedding as a capability layer</h2>
        <p>
          Self-host Seal behind your product API or agent runtime. You own identity and UX; Seal
          provides guardrails, validated SQL, charts, and optional chat sessions. See{' '}
          <Link href="/docs/embedding">Embedding Seal</Link> for the BFF pattern, deployment options,
          and the scope → SQL → RAG boundaries.
        </p>

        <h2 id="multi-database">Multi-database routing</h2>
        <p>
          Register named backends at startup; clients pass <code>database_id</code> on query, chat,
          and schema requests.
        </p>
        <ul>
          <li>
            <code>DATABASE_URL</code> → id <code>default</code>
          </li>
          <li>
            Optional <code>config/databases.yaml</code> or <code>SEAL_DATABASES</code> JSON for
            additional ids
          </li>
          <li>
            Unknown id → HTTP 404 <code>unknown_database_id</code>
          </li>
          <li>
            Global catalog and vector index remain on default —{' '}
            <Link href="/docs/multi-database">Multi-database routing</Link>
          </li>
        </ul>

        <h2 id="guardrails">LLM guardrails</h2>
        <p>
          Scope classification runs before planners, SQL, and vector RAG on query and chat paths.
        </p>
        <ul>
          <li>
            <strong>In scope:</strong> analytics, schema/catalog help, data-grounded Q&amp;A
          </li>
          <li>
            <strong>Chat out-of-scope:</strong> HTTP 200 refusal with{' '}
            <code>metadata.suggested_queries</code> (no SQL)
          </li>
          <li>
            <strong>Query out-of-scope:</strong> HTTP 400 structured{' '}
            <code>detail</code> with <code>suggested_queries</code>
          </li>
          <li>
            Configurable via <code>GUARDRAILS_*</code> and workspace —{' '}
            <Link href="/docs/guardrails">Guardrails</Link>
          </li>
        </ul>

        <h2 id="chat">Schema-grounded chat</h2>
        <p>
          <code>POST /v1/chat</code> provides conversational analytics with session memory.
        </p>
        <ul>
          <li>
            <code>session_id</code> for follow-ups · <code>include_charts</code> ·{' '}
            <code>stream=true</code> for SSE
          </li>
          <li>
            <code>enhancement</code> per-request override of <code>CHAT_ENHANCEMENT_ENABLED</code>
          </li>
          <li>
            Rejects <code>system</code> role in <code>messages</code> overrides (HTTP 400)
          </li>
        </ul>
        <p>
          <Link href="/docs/chat-qa">Chat &amp; Q&amp;A</Link> ·{' '}
          <DocLink href="/docs/execution-metadata">Execution metadata</DocLink> ·{' '}
          <Link href="/docs/chat-streaming">Streaming</Link>
        </p>

        <h2 id="enhancement">Prompt enhancement</h2>
        <p>Default chain before SQL generation (can disable per request):</p>
        <ol>
          <li>Schema-aware table/column context</li>
          <li>Optional vector RAG over catalog metadata (<code>VECTOR_STORE=chroma</code>)</li>
          <li>Multi-turn conversation summarization</li>
        </ol>
        <p>
          <Link href="/docs/prompt-enhancement">Prompt enhancement</Link> ·{' '}
          <Link href="/docs/vector-rag">Vector RAG</Link>
        </p>

        <h2 id="workspace">Workspace settings</h2>
        <p>
          Operator settings and catalog description overrides persist in Postgres (
          <code>seal_app.workspace_kv</code>), with file and <code>.env</code> fallbacks.
        </p>
        <ul>
          <li>
            Hot-reload guardrails and limits in dev; <strong>Apply to API</strong> in production
          </li>
          <li>
            <Link href="/docs/workspace">Workspace settings</Link> · dashboard Settings page
          </li>
        </ul>

        <h2 id="charts">Charts &amp; visualization</h2>
        <p>
          The chart engine inspects result shape and emits Vega-Lite JSON (bar, line, area, pie,
          scatter, table, metric_card).
        </p>
        <ul>
          <li>
            React: <code>{'<VegaChart spec={result.chart} />'}</code> from the TS SDK
          </li>
          <li>
            <Link href="/docs/charts-analysis">Charts &amp; analysis</Link> ·{' '}
            <Link href="/demo">Demo</Link>
          </li>
        </ul>

        <h2 id="dashboard">Operational dashboard</h2>
        <p>
          <code>apps/web</code> (port <strong>3001</strong>) is a live API console — not fixture-based.
          Exercises Query, Chat (SSE), Catalog editor, Workspace settings, and Vector reindex against
          your running backend.
        </p>
        <p>
          <Link href="/docs/dashboard">Dashboard guide</Link>
        </p>

        <h2 id="auth">API authentication</h2>
        <p>
          Shared secret <code>SEAL_API_KEY</code> → <code>X-API-Key</code> on <code>/v1/*</code>.{' '}
          <code>GET /health</code> stays public. Production: generate with{' '}
          <code>openssl rand -hex 32</code>, <code>SEAL_DEV_MODE=false</code>, optional{' '}
          <code>SEAL_DISABLE_DOCS=true</code>.
        </p>
        <p>
          <Link href="/docs/authentication">Authentication</Link>
        </p>

        <h2 id="agents">Agent frameworks</h2>
        <p>
          OpenAI-format tool manifest (<code>seal-tools.openai.json</code>):{' '}
          <code>seal_get_schema</code>, <code>seal_get_catalog</code>, <code>seal_query</code>,{' '}
          <code>seal_chat</code>. Use <code>enhancement: false</code> when your agent already has RAG.
        </p>
        <p>
          <Link href="/docs/agent-frameworks">Agent frameworks</Link>
        </p>

        <h2 id="sdks">SDKs &amp; OpenAPI</h2>
        <ul>
          <li>
            Python <code>seal</code> — sync, async, <code>chat_stream</code>
          </li>
          <li>
            TypeScript <code>seal</code> — <code>chatStream</code>, optional React{' '}
            <code>VegaChart</code>
          </li>
          <li>
            Committed <a href="/openapi.json">openapi.json</a> · live Swagger at{' '}
            <code>/docs</code> when enabled
          </li>
        </ul>

        <Callout variant="info" title="Feature matrix vs deployment">
          Vector RAG and Chroma require <code>SEAL_EXTRA=chroma</code> at image build and{' '}
          <code>VECTOR_STORE=chroma</code> at runtime. Default compose uses{' '}
          <code>VECTOR_STORE=none</code> — enhancement still runs without embeddings.
        </Callout>
      </DocsProse>
    </div>
  );
}
