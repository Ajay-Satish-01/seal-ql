import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { Callout } from '@/components/docs/callout';
import { SITE } from '@/lib/constants';
import {
  curlChat,
  localDevSetupSnippet,
  productionCatalogEnvSnippet,
  pythonChatSnippet,
  pythonQuerySnippet,
  tsChatSnippet,
} from '@/lib/doc-snippets';

export default function IntegrationGuidePage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Integration Guide"
        description="Connect your application to a self-hosted Seal API."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <Callout variant="info" title="Recommended path">
          Docker image → SDK install → set <code>baseUrl</code>. You do not need to clone the
          repository to integrate.
        </Callout>

        <h2 id="docker" className="text-foreground mt-10 text-2xl font-bold">
          1. Run the API (Docker)
        </h2>
        <p>
          Follow <Link href="/docs/self-hosting">Self-Hosting</Link> to pull{' '}
          <code>{SITE.dockerImage}</code> and start the compose stack. Confirm health:
        </p>
        <CodeBlock language="bash" code="curl http://localhost:8000/health" />

        <h2 className="text-foreground mt-10 text-2xl font-bold">1a. Data catalog (recommended)</h2>
        <p>
          Mount <code>./config</code> and let the API sync business descriptions into{' '}
          <code>catalog.yaml</code> on startup. Improves both query and chat accuracy.
        </p>
        <CodeBlock language="bash" code={productionCatalogEnvSnippet()} />
        <p>
          Contributors: <code>make sync-catalog</code> after <code>make seed</code>. Details:{' '}
          <Link href="/docs/data-catalog">Data catalog</Link>.
        </p>

        <h2 id="llm" className="text-foreground mt-10 text-2xl font-bold">
          1b. Configure the LLM (LiteLLM)
        </h2>
        <p>
          The planner uses{' '}
          <a
            href="https://docs.litellm.ai/docs/providers"
            className="text-primary hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            LiteLLM
          </a>
          . Set <code>LLM_MODEL</code> to a LiteLLM provider string (
          <code>ollama/…</code>, <code>gemini/…</code>, <code>openai/…</code>,{' '}
          <code>anthropic/…</code>) and provide the matching API key env vars LiteLLM expects.
        </p>
        <p>
          Use <code>OLLAMA_PROFILE=disabled</code> for cloud providers; leave the profile at{' '}
          <code>default</code> (or omit it) for bundled Ollama with <code>LLM_BASE_URL</code>.
        </p>
        <CodeBlock
          language="bash"
          code={`# Ollama — .env next to docker-compose.example.yml
LLM_MODEL=ollama/llama3.2:1b
LLM_BASE_URL=http://ollama:11434

# Cloud (Gemini) — same file, different values
OLLAMA_PROFILE=disabled
LLM_MODEL=gemini/gemini-1.5-flash
GEMINI_API_KEY=your-key-here`}
        />
        <p>
          Model ids, keys, and compose profiles:{' '}
          <Link href="/docs/self-hosting#llm-configuration">Self-Hosting → LLM configuration</Link>.
        </p>

        <h2 id="sdk" className="text-foreground mt-10 text-2xl font-bold">
          2. Install the SDK
        </h2>
        <CodeBlock
          language="bash"
          code={`# Python
pip install seal

# TypeScript / React
npm install seal
npm install react react-dom vega vega-lite vega-embed`}
        />

        <h2 className="text-foreground mt-10 text-2xl font-bold">3. Connect</h2>
        <p>
          Set <code>baseUrl</code> to your API (local or internal). Use HTTPS in production behind
          your proxy.
        </p>
        <CodeBlock
          language="typescript"
          code={`import { Seal } from 'seal';

const client = new Seal({
  baseUrl: 'https://seal.internal.example.com',
  apiKey: process.env.SEAL_API_KEY, // X-API-Key header
});

const result = await client.query('Hourly event counts');
console.log(result.sql, result.results, result.chart);`}
        />
        <CodeBlock
          language="python"
          code={pythonQuerySnippet('https://seal.internal.example.com', 'Hourly event counts')}
        />
        <p>
          Python: <Link href="/docs/python-sdk">Python SDK</Link> · TypeScript:{' '}
          <Link href="/docs/typescript-sdk">TypeScript SDK</Link>
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">3b. API authentication</h2>
        <p>
          Set <code>SEAL_API_KEY</code> on the server. In production use{' '}
          <code>SEAL_AUTH_REQUIRED=true</code>, <code>SEAL_DEV_MODE=false</code>, and{' '}
          <code>SEAL_DISABLE_DOCS=true</code>. Clients send <code>X-API-Key</code>; the TypeScript
          SDK&apos;s <code>apiKey</code> option overrides any <code>X-API-Key</code> in custom{' '}
          <code>headers</code>. <code>/health</code> stays public. See{' '}
          <Link href="/docs/authentication">Authentication</Link>.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">3c. Multiple databases (optional)</h2>
        <p>
          If you have more than one SQL backend (Postgres + DuckDB analytics file, read replica, etc.),
          register extra ids in <code>config/databases.yaml</code> or <code>SEAL_DATABASES</code>, then
          pass <code>database_id</code> on <code>/v1/query</code>, <code>/v1/chat</code>, and{' '}
          <code>/v1/schema</code>. Clients never send raw connection URLs.
        </p>
        <p>
          Full walkthrough with curl, SDK, session pinning, and DuckDB paths:{' '}
          <Link href="/docs/multi-database">Multi-database routing</Link>.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">3d. Conversational Q&amp;A</h2>
        <p>
          Use <code>POST /v1/chat</code> for multi-turn questions, optional charts, and streaming.
          Pass <code>session_id</code> from the previous response for follow-ups, and repeat the same{' '}
          <code>database_id</code> on every turn once the session is pinned.
        </p>
        <CodeBlock
          language="typescript"
          code={tsChatSnippet(SITE.defaultBaseUrl, 'Orders by region last week', {
            includeCharts: true,
          })}
        />
        <CodeBlock language="bash" code={curlChat(SITE.defaultBaseUrl, 'Orders by region last week', { includeCharts: true })} />
        <CodeBlock
          language="python"
          code={pythonChatSnippet(SITE.defaultBaseUrl, 'Orders by region last week', {
            includeCharts: true,
          })}
        />
        <p>
          <Link href="/docs/chat-qa">Chat &amp; Q&A</Link> ·{' '}
          <Link href="/docs/data-catalog">Data catalog</Link> ·{' '}
          <Link href="/docs/chat-streaming">Streaming</Link>
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">4. HTTP / OpenAPI</h2>
        <p>
          Without an SDK, call <code>POST /v1/query</code> with JSON{' '}
          <code>{'{ "query": "..." }'}</code> or <code>POST /v1/chat</code> with{' '}
          <code>{'{ "message": "..." }'}</code>. Download{' '}
          <a href="/openapi.json" className="text-primary">
            openapi.json
          </a>{' '}
          or use live Swagger at <code>{'{baseUrl}'}/docs</code> when{' '}
          <code>SEAL_DISABLE_DOCS=false</code> (typical local dev; hidden in production compose).
        </p>
        <p>
          <Link href="/docs/api-reference">API Reference</Link>
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">5. Build a dashboard</h2>
        <ul>
          <li>
            <code>results</code> + <code>columns</code> for tables
          </li>
          <li>
            <code>chart.chart_type</code> — bar, line, pie, scatter, area use Vega-Lite; table and
            metric_card render from rows
          </li>
          <li>
            React: <code>&lt;VegaChart spec={'{result.chart}'} /&gt;</code>
          </li>
        </ul>
        <p>
          <Link href="/docs/charts-analysis">Charts &amp; Analysis</Link> ·{' '}
          <Link href="/demo">Interactive demo</Link>
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">6. Schema-first queries</h2>
        <p>
          Call <code>GET /v1/schema</code> (or <code>client.schema()</code>) to inspect tables
          before asking NL questions. Sample seed includes <code>products</code>,{' '}
          <code>orders</code>, <code>events_hourly</code>, <code>product_performance</code>.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">7. Workspace &amp; guardrails</h2>
        <p>
          Tune scope gates and input limits without redeploying:{' '}
          <Link href="/docs/workspace">Workspace settings</Link> and{' '}
          <Link href="/docs/guardrails">Guardrails</Link>. The dashboard Settings page writes to
          Postgres; use <strong>Apply to API</strong> in production after PATCH.
        </p>
        <p className="text-muted-foreground mt-3 text-sm leading-relaxed">
          Off-topic <strong>query</strong> calls return HTTP 400 with structured{' '}
          <code>detail</code> (<code>query_out_of_scope</code>, <code>reason</code>,{' '}
          <code>suggested_queries</code>) — handle <code>QueryOutOfScopeError</code> in the SDKs.
          Off-topic <strong>chat</strong> returns HTTP 200 with <code>metadata.refusal</code> and the
          same suggestion list (flat on <code>seal.meta</code> when streaming).
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">8. Troubleshooting</h2>
        <ul>
          <li>
            <strong>Connection refused</strong> — check container health and port mapping.
          </li>
          <li>
            <strong>CORS</strong> — add your frontend origin to <code>CORS_ORIGINS</code>.
          </li>
          <li>
            <strong>LLM timeouts</strong> — Ollama: confirm the model finished pulling; cloud: check
            quota and that <code>LLM_MODEL</code> matches your API key provider.
          </li>
          <li>
            <strong>Model / profile mismatch</strong> — cloud models (
            <code>gemini/</code>, <code>openai/</code>, …) require{' '}
            <code>OLLAMA_PROFILE=disabled</code>; check API startup warnings in the logs.
          </li>
          <li>
            <strong>Version skew</strong> — align Docker image tag with SDK version.
          </li>
        </ul>

        <h2 className="text-foreground mt-10 text-2xl font-bold">9. Verify with E2E tests</h2>
        <p>
          After <code>make up && make seed</code>, run <code>make check-e2e</code> to exercise live
          HTTP tests (same as CI). Details: <Link href="/docs/testing">Testing &amp; CI</Link>.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Advanced: develop from source</h2>
        <CodeBlock language="bash" code={localDevSetupSnippet()} />
        <p>
          See <Link href="/docs/contributing">Contributing</Link> for tooling and{' '}
          <code>make sync-docs-assets</code>.
        </p>
      </div>
    </div>
  );
}
