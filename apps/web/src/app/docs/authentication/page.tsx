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
        description="Protect your self-hosted Seal API with a shared API key."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <p>
          Seal uses a single shared secret for machine-to-machine access. When configured, every{' '}
          <code>/v1/*</code> route requires the <code>X-API-Key</code> HTTP header. The health
          endpoint stays public so load balancers and orchestrators can probe without credentials.
        </p>

        <Callout variant="warning" title="Production">
          Set <code>SEAL_API_KEY</code> to a long random value,{' '}
          <code>SEAL_AUTH_REQUIRED=true</code>, <code>SEAL_DEV_MODE=false</code>, and{' '}
          <code>SEAL_DISABLE_DOCS=true</code>. Placeholder keys (e.g.{' '}
          <code>dev-local-change-me</code>) are rejected when auth is required{' '}
          <em>or</em> dev mode is off — even if <code>SEAL_DEV_MODE</code> was left on by mistake.
          Never commit secrets to git or put <code>SEAL_API_KEY</code> in browser or mobile apps.
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
          internal capability layer.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">How it works</h2>
        <ol>
          <li>
            The API reads <code>SEAL_API_KEY</code> from the environment (empty or whitespace-only
            values are treated as unset).
          </li>
          <li>
            When a key is set, <code>POST /v1/query</code> and <code>GET /v1/schema</code> run
            through a FastAPI dependency that compares the client header with{' '}
            <code>secrets.compare_digest</code> (constant-time).
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
              description:
                'Shared secret. When set, clients must send X-API-Key with this exact value on /v1/* routes.',
            },
            {
              name: 'SEAL_AUTH_REQUIRED',
              type: 'boolean',
              required: true,
              description:
                'When true, startup fails without a real SEAL_API_KEY (no placeholders). Runtime /v1/* auth still follows whether SEAL_API_KEY is set.',
            },
            {
              name: 'SEAL_DISABLE_DOCS',
              type: 'boolean',
              description:
                'Hide /docs, /redoc, /openapi.json. Defaults to SEAL_AUTH_REQUIRED when unset.',
            },
            {
              name: 'SEAL_DEV_MODE',
              type: 'boolean',
              description:
                'When true (and SEAL_AUTH_REQUIRED=false), allows placeholder API keys for local dev. Ignored for placeholders if SEAL_AUTH_REQUIRED=true. Must be false in production.',
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
SEAL_AUTH_REQUIRED=true
SEAL_DEV_MODE=false
SEAL_DISABLE_DOCS=true`}
        />
        <p>
          For <strong>repo development</strong>, copy <code>.env.example</code> → <code>.env</code>{' '}
          (placeholder key + <code>SEAL_DEV_MODE=true</code>) and run <code>make up</code>. Image-only
          production compose requires a real <code>SEAL_API_KEY</code> in <code>.env</code> with no
          default. See <Link href="/docs/self-hosting">Self-Hosting</Link> and{' '}
          <Link href="/docs/contributing">Contributing</Link>.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Abuse protection</h2>
        <p>
          Seal does not ship in-process rate limits. For internet-facing query endpoints, use your
          reverse proxy or API gateway (nginx, Cloudflare, AWS WAF) to throttle failed auth and
          expensive <code>POST /v1/query</code> calls.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">SDK clients</h2>
        <p>
          Pass the same secret to the SDK; it sets <code>X-API-Key</code> on every request
          (including <code>/v1/query</code> and <code>/v1/schema</code>). Health checks do not
          need the key.
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

        <h2 className="text-foreground mt-10 text-2xl font-bold">Modes</h2>
        <table className="border-border/50 my-6 w-full border-collapse border text-left text-sm">
          <thead className="bg-muted/80">
            <tr>
              <th className="border-border/50 border p-2">SEAL_API_KEY</th>
              <th className="border-border/50 border p-2">SEAL_AUTH_REQUIRED</th>
              <th className="border-border/50 border p-2">SEAL_DEV_MODE</th>
              <th className="border-border/50 border p-2">Behavior</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border-border/50 border p-2 font-mono text-xs">unset</td>
              <td className="border-border/50 border p-2 font-mono text-xs">false</td>
              <td className="border-border/50 border p-2 font-mono text-xs">any</td>
              <td className="border-border/50 border p-2">
                Open <code>/v1/*</code> (trusted local networks only).
              </td>
            </tr>
            <tr>
              <td className="border-border/50 border p-2 font-mono text-xs">set (real secret)</td>
              <td className="border-border/50 border p-2 font-mono text-xs">false</td>
              <td className="border-border/50 border p-2 font-mono text-xs">false</td>
              <td className="border-border/50 border p-2">
                <code>/v1/*</code> requires matching <code>X-API-Key</code>.
              </td>
            </tr>
            <tr>
              <td className="border-border/50 border p-2 font-mono text-xs">placeholder</td>
              <td className="border-border/50 border p-2 font-mono text-xs">false</td>
              <td className="border-border/50 border p-2 font-mono text-xs">true</td>
              <td className="border-border/50 border p-2">
                Repo <code>make up</code> / <code>.env.example</code> local dev only.
              </td>
            </tr>
            <tr>
              <td className="border-border/50 border p-2 font-mono text-xs">set (real secret)</td>
              <td className="border-border/50 border p-2 font-mono text-xs">true</td>
              <td className="border-border/50 border p-2 font-mono text-xs">false</td>
              <td className="border-border/50 border p-2">
                Recommended production: auth enforced at startup and runtime.
              </td>
            </tr>
            <tr>
              <td className="border-border/50 border p-2 font-mono text-xs">placeholder</td>
              <td className="border-border/50 border p-2 font-mono text-xs">true</td>
              <td className="border-border/50 border p-2 font-mono text-xs">true</td>
              <td className="border-border/50 border p-2">
                Startup fails — placeholders never allowed when auth is required.
              </td>
            </tr>
            <tr>
              <td className="border-border/50 border p-2 font-mono text-xs">unset</td>
              <td className="border-border/50 border p-2 font-mono text-xs">true</td>
              <td className="border-border/50 border p-2 font-mono text-xs">any</td>
              <td className="border-border/50 border p-2">
                API process exits on startup with a configuration error.
              </td>
            </tr>
          </tbody>
        </table>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Errors</h2>
        <ul>
          <li>
            <strong>401 Unauthorized</strong> — missing or invalid <code>X-API-Key</code> on a
            protected route.
          </li>
          <li>
            <strong>503 Service Unavailable</strong> — rare misconfiguration if auth is required but
            the key was cleared at runtime (startup normally prevents this).
          </li>
        </ul>
        <p>
          SDKs map 4xx responses to <code>QueryError</code> (including 401). See{' '}
          <Link href="/docs/api-reference">API Reference</Link>. Live Swagger at{' '}
          <code>/docs</code> is available only when <code>SEAL_DISABLE_DOCS=false</code> (typical
          local dev).
        </p>
      </div>
    </div>
  );
}
