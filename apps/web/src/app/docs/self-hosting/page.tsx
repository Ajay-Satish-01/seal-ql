import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { Callout } from '@/components/docs/callout';
import { ParamTable } from '@/components/docs/param-table';
import { SITE } from '@/lib/constants';
import { getComposeExample } from '@/lib/compose-example';
import { LlmConfigSection } from '@/components/docs/llm-config';

export default function SelfHostingPage() {
  const composeYaml = getComposeExample();

  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Self-Hosting with Docker"
        description="Run Seal on your infrastructure using the published image — no git clone required."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <Callout variant="success" title="Image-first">
          Pull <code>{SITE.dockerImage}</code> from Docker Hub. Copy the compose file below — it
          uses <code>image:</code>, not <code>build:</code>.
        </Callout>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Quick start</h2>
        <CodeBlock
          language="bash"
          code={`docker pull ${SITE.dockerImage}

mkdir seal && cd seal
# Download docker-compose.example.yml and seed.sql (links below)
export SEAL_API_KEY=$(openssl rand -hex 32)
printf '%s\\n' \\
  "SEAL_API_KEY=$SEAL_API_KEY" \\
  "SEAL_AUTH_REQUIRED=true" \\
  "SEAL_DEV_MODE=false" \\
  "SEAL_DISABLE_DOCS=true" \\
  > .env

docker compose -f docker-compose.example.yml up -d
curl http://localhost:8000/health`}
        />

        <p>
          Download assets from this site:{' '}
          <a href="/compose/docker-compose.example.yml" className="text-primary">
            docker-compose.example.yml
          </a>
          ,{' '}
          <a href="/samples/seed.sql" className="text-primary">
            seed.sql
          </a>
          . Place <code>seed.sql</code> next to the compose file (mounted on first Postgres start).
        </p>

        <h3 className="text-foreground mt-8 text-lg font-semibold">Example compose</h3>
        <CodeBlock language="yaml" code={composeYaml} />

        <LlmConfigSection />

        <h2 className="text-foreground mt-10 text-2xl font-bold">Other environment variables</h2>
        <p>
          API keys: <Link href="/docs/authentication">Authentication</Link>.
        </p>

        <ParamTable
          rows={[
            {
              name: 'SEAL_API_KEY',
              type: 'string',
              description:
                'Shared secret for X-API-Key on /v1/*. Set with SEAL_AUTH_REQUIRED=true in production.',
            },
            {
              name: 'SEAL_AUTH_REQUIRED',
              type: 'boolean',
              description: 'When true, the API fails startup without a real key (no placeholders).',
            },
            {
              name: 'SEAL_DISABLE_DOCS',
              type: 'boolean',
              description:
                'Hide Swagger and /openapi.json. Production example defaults to true; when unset, follows SEAL_AUTH_REQUIRED.',
            },
            {
              name: 'SEAL_DEV_MODE',
              type: 'boolean',
              description:
                'Must be false in production. When true with SEAL_AUTH_REQUIRED=false, allows placeholder keys for local dev only.',
            },
            {
              name: 'DATABASE_URL',
              type: 'string',
              description: 'Postgres/asyncpg URL for introspection and execution.',
            },
            {
              name: 'CORS_ORIGINS',
              type: 'JSON array',
              description: 'Allowed browser origins for your frontend.',
            },
            {
              name: 'MAX_ROWS',
              type: 'integer',
              description: 'Hard cap on returned rows (default 10000).',
            },
            {
              name: 'QUERY_TIMEOUT_SECONDS',
              type: 'integer',
              description: 'SQL execution timeout (default 30).',
            },
          ]}
        />

        <h2 className="text-foreground mt-10 text-2xl font-bold">Production patterns</h2>
        <ul>
          <li>
            <strong>API only:</strong> Run the API container with your external Postgres{' '}
            <code>DATABASE_URL</code> — skip bundled Postgres/Ollama services.
          </li>
          <li>
            <strong>Cloud LLM:</strong> Set <code>OLLAMA_PROFILE=disabled</code> and provide{' '}
            <code>LLM_MODEL</code> plus an API key (see LLM section above). No{' '}
            <code>LLM_BASE_URL</code> required.
          </li>
          <li>
            <strong>TLS:</strong> Terminate HTTPS at your reverse proxy; keep the API on an internal
            network.
          </li>
        </ul>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Verify</h2>
        <CodeBlock
          language="bash"
          code={`curl http://localhost:8000/health

# Production compose requires X-API-Key (value from your .env)
curl -H "X-API-Key: $SEAL_API_KEY" http://localhost:8000/v1/schema

curl -s -X POST http://localhost:8000/v1/query \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: $SEAL_API_KEY" \\
  -d '{"query": "Show total revenue by product category", "database_id": "default"}' \\
| python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('chart',{}).get('chart_type'), d.get('detail','OK')[:80])"`}
        />

        <p className="mt-8">
          Next: <Link href="/docs/integration-guide">Integration Guide</Link> ·{' '}
          <a href={SITE.dockerHub} target="_blank" rel="noreferrer" className="text-primary">
            Docker Hub
          </a>
        </p>
      </div>
    </div>
  );
}
