import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { Callout } from '@/components/docs/callout';
import { ParamTable } from '@/components/docs/param-table';

export default function AuthenticationPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Authentication"
        description="Every Seal deployment requires a shared API key on /v1/*."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <p>
          Seal <strong>always</strong> requires <code>SEAL_API_KEY</code> at startup. The API refuses
          to boot without a real secret, and every <code>/v1/*</code> route expects the{' '}
          <code>X-API-Key</code> header to match. Only <code>GET /health</code> stays public for
          probes.
        </p>

        <Callout variant="warning" title="Dashboard and .env must match">
          Generate <code>SEAL_API_KEY</code> with <code>openssl rand -hex 32</code>, set it in the API{' '}
          <code>.env</code>, and paste the <strong>same value</strong> into the operational dashboard{' '}
          (<code>apps/web</code>) <code>X-API-Key</code> field when you connect. Documented placeholders
          (e.g. <code>dev-local-change-me</code>) are rejected at startup. Never commit production
          secrets to git or ship <code>SEAL_API_KEY</code> to browsers or mobile apps.
        </Callout>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Who should call Seal?</h2>
        <p>
          <strong>Your backend (recommended):</strong> End users sign in to your product (Cognito,
          Auth0, sessions). Your server holds <code>SEAL_API_KEY</code> and calls Seal — users never
          see the key.
        </p>
        <p>
          <strong>Exposing Seal to end users:</strong> Do not give customers the shared API key. Put
          your own API or API gateway in front with per-user JWT, rate limits, and TLS. Seal stays an
          internal capability layer. See <Link href="/docs/embedding">Embedding Seal</Link> for
          responsibility split, deployment patterns, and the scope → SQL → RAG boundaries.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">How it works</h2>
        <ol>
          <li>
            <code>SEAL_API_KEY</code> must be set in the environment (empty or whitespace-only values
            are rejected at startup).
          </li>
          <li>
            All <code>/v1/*</code> routes (including <code>POST /v1/query</code>,{' '}
            <code>POST /v1/chat</code>, <code>GET /v1/catalog</code>, and <code>GET /v1/schema</code>)
            compare the client <code>X-API-Key</code> header with <code>secrets.compare_digest</code>{' '}
            (constant-time).
          </li>
          <li>
            Missing or wrong keys return <strong>401</strong> with a generic message (no hint about
            which part failed).
          </li>
          <li>
            <code>GET /health</code> is always unauthenticated.
          </li>
        </ol>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Environment variables</h2>
        <ParamTable
          rows={[
            {
              name: 'SEAL_API_KEY',
              type: 'string',
              required: true,
              description:
                'Shared secret required at startup. Clients must send X-API-Key with this exact value on /v1/* routes.',
            },
            {
              name: 'SEAL_DISABLE_DOCS',
              type: 'boolean',
              description:
                'Hide /docs, /redoc, /openapi.json. Defaults to false (docs enabled). Set true for internet-facing deployments.',
            },
            {
              name: 'SEAL_DEV_MODE',
              type: 'boolean',
              description:
                'When true, workspace PATCH hot-reloads guardrails and LLM settings without POST /v1/workspace/settings/apply. Must be false in production.',
            },
          ]}
        />

        <h2 className="text-foreground mt-10 text-2xl font-bold">Generate a key</h2>
        <CodeBlock language="bash" code="openssl rand -hex 32" />

        <h2 className="text-foreground mt-10 text-2xl font-bold">Docker / compose</h2>
        <CodeBlock
          language="bash"
          code={`# Production .env next to docker-compose.example.yml
SEAL_API_KEY=$(openssl rand -hex 32)
SEAL_DEV_MODE=false
SEAL_DISABLE_DOCS=true`}
        />
        <p>
          For <strong>repo development</strong>, copy <code>.env.example</code> → <code>.env</code>{' '}
          (includes a documented local-only test key), run <code>make up</code>, then paste the same
          key into the dashboard <strong>Connect</strong> bar. For anything shared or production-like,
          replace it with <code>openssl rand -hex 32</code>. See{' '}
          <Link href="/docs/self-hosting">Self-Hosting</Link> and{' '}
          <Link href="/docs/contributing">Contributing</Link>.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Abuse protection</h2>
        <p>
          <strong>LLM guardrails</strong> — Every <code>POST /v1/query</code> and{' '}
          <code>POST /v1/chat</code> request passes a scope gate (input limits, heuristics, and an
          LLM classifier). Analytics and schema/catalog questions stay in scope; off-topic prompts
          get a chat refusal (HTTP 200, <code>metadata.suggested_queries</code>) or structured{' '}
          <code>query_out_of_scope</code> (HTTP 400). Configure via <code>GUARDRAILS_*</code> and{' '}
          <code>MAX_*_CHARS</code> in <code>.env</code>, or hot-reload from the dashboard Settings page
          in dev. Full guide: <Link href="/docs/guardrails">Guardrails</Link>.
        </p>
        <p>
          <strong>Rate limits</strong> — Seal does not ship in-process HTTP rate limits. For
          internet-facing deployments, use your reverse proxy or API gateway (nginx, Cloudflare,
          AWS WAF) to throttle failed auth and expensive <code>POST /v1/query</code> calls.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">SDK clients</h2>
        <p>
          Pass the same secret to the SDK; it sets <code>X-API-Key</code> on every request (including{' '}
          <code>/v1/query</code> and <code>/v1/schema</code>). Health checks do not need the key.
        </p>
        <CodeBlock
          language="python"
          code={`from seal import Seal

with Seal("http://localhost:8000", api_key="your-secret") as client:
    schema = client.schema()
    result = client.query("Revenue by month")`}
        />
        <CodeBlock
          language="typescript"
          code={`import { Seal } from 'seal';

const client = new Seal({
  baseUrl: 'http://localhost:8000',
  apiKey: process.env.SEAL_API_KEY!,
});`}
        />
        <p>
          <Link href="/docs/python-sdk">Python SDK</Link> ·{' '}
          <Link href="/docs/typescript-sdk">TypeScript SDK</Link>
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Raw HTTP</h2>
        <CodeBlock
          language="bash"
          code={`curl -s http://localhost:8000/health

curl -s -H "X-API-Key: your-secret" http://localhost:8000/v1/schema

curl -s -X POST http://localhost:8000/v1/query \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: your-secret" \\
  -d '{"query": "Show total revenue"}'`}
        />

        <h2 className="text-foreground mt-10 text-2xl font-bold">Errors</h2>
        <ul>
          <li>
            <strong>401 Unauthorized</strong> — missing or invalid <code>X-API-Key</code> on a
            protected route.
          </li>
          <li>
            <strong>503 Service Unavailable</strong> — LiteLLM rate limit on query/chat/vector routes,
            or rare auth misconfiguration if the key was cleared at runtime.
          </li>
          <li>
            <strong>502 Bad Gateway</strong> — LiteLLM provider failure on query, chat, or vector
            reindex (missing API key, invalid model, provider error). Response <code>detail</code> is
            safe for clients.
          </li>
        </ul>
        <p>
          SDKs map 4xx responses to <code>QueryError</code> (including 401). See{' '}
          <Link href="/docs/api-reference">API Reference</Link>. Live Swagger at <code>/docs</code> is
          available when <code>SEAL_DISABLE_DOCS=false</code> (typical local dev).
        </p>
      </div>
    </div>
  );
}
