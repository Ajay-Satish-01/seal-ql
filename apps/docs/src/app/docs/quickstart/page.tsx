import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { Callout } from '@/components/docs/callout';
import { DocsProse } from '@/components/docs/docs-prose';
import { PortsTable } from '@/components/docs/ports-table';
import { SetupChecklist, SetupDoneBanner } from '@/components/docs/setup-checklist';
import { SITE } from '@/lib/constants';
import { pythonChatSnippet, tsQuerySnippet, fullLocalVerifySnippet } from '@/lib/doc-snippets';
import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export default function QuickstartPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Quickstart"
        description="From zero to a working NL → SQL → chart flow in under fifteen minutes."
      />

      <DocsProse>
        <Callout variant="success" title="Two paths">
          <strong>Integrators</strong> — Docker image + SDK (sections 1–4). No git clone required.{' '}
          <strong>Contributors</strong> — clone the repo, <code>make up</code>, and{' '}
          <code>make seed</code> (section 5).
        </Callout>

        <h2>Local ports</h2>
        <PortsTable />

        <h2>Step-by-step (integrators)</h2>
      </DocsProse>

      <SetupChecklist
        steps={[
          {
            title: 'Try the fixture demo (no API)',
            body: (
              <p>
                Open the{' '}
                <Link href="/demo" className="text-primary hover:underline">
                  interactive demo
                </Link>{' '}
                to see NL → SQL → Vega-Lite with pre-generated responses — useful before Docker is
                running.
              </p>
            ),
          },
          {
            title: 'Run the API with Docker',
            body: (
              <>
                <p>
                  Pull <code>{SITE.dockerImage}</code> and use the production compose example from{' '}
                  <Link href="/docs/self-hosting" className="text-primary hover:underline">
                    Self-hosting
                  </Link>
                  . Generate a real <code>SEAL_API_KEY</code> — never use placeholders in production.
                </p>
              </>
            ),
            code: `docker pull ${SITE.dockerImage}
mkdir seal-quickstart && cd seal-quickstart
curl -O https://raw.githubusercontent.com/seal/seal/main/apps/docs/public/compose/docker-compose.example.yml
curl -O https://raw.githubusercontent.com/seal/seal/main/apps/docs/public/samples/seed.sql

printf '%s\\n' \\
  "SEAL_API_KEY=$(openssl rand -hex 32)" \\
  "SEAL_AUTH_REQUIRED=true" \\
  "SEAL_DEV_MODE=false" \\
  "SEAL_DISABLE_DOCS=true" \\
  > .env

mkdir config
docker compose -f docker-compose.example.yml up -d
curl -s http://localhost:8000/health`,
          },
          {
            title: 'Configure the LLM (LiteLLM)',
            body: (
              <p>
                Set <code>LLM_MODEL</code> to a LiteLLM provider id (
                <code>ollama/llama3.2:1b</code>, <code>gemini/gemini-2.0-flash</code>, etc.). Local
                Ollama: default profile + <code>LLM_BASE_URL</code>. Cloud:{' '}
                <code>OLLAMA_PROFILE=disabled</code> + provider API key. See{' '}
                <Link href="/docs/self-hosting#llm-configuration" className="text-primary hover:underline">
                  LLM configuration
                </Link>
                .
              </p>
            ),
          },
          {
            title: 'Enable catalog & chat (recommended)',
            body: (
              <p>
                Mount <code>./config</code>, set <code>CATALOG_AUTO_SYNC=true</code>, and{' '}
                <code>CHAT_ENHANCEMENT_ENABLED=true</code>. Add business descriptions via{' '}
                <Link href="/docs/data-catalog" className="text-primary hover:underline">
                  Data catalog
                </Link>{' '}
                or the dashboard.
              </p>
            ),
          },
          {
            title: 'Install the SDK and query',
            body: (
              <p>
                Pass <code>apiKey</code> / <code>api_key</code> when the server requires{' '}
                <code>X-API-Key</code>. See{' '}
                <Link href="/docs/authentication" className="text-primary hover:underline">
                  Authentication
                </Link>
                .
              </p>
            ),
            code: 'pip install seal\n# or: npm install seal',
          },
        ]}
      />

      <div className="mt-6 space-y-4">
        <CodeBlock
          language="typescript"
          code={tsQuerySnippet(SITE.defaultBaseUrl, 'Show total revenue by product category')}
        />
        <CodeBlock
          language="python"
          code={pythonChatSnippet(SITE.defaultBaseUrl, 'What drove revenue last quarter?', {
            includeCharts: true,
          })}
        />
      </div>

      <DocsProse>
        <h2 className="mt-12">Step-by-step (from source)</h2>
      </DocsProse>

      <SetupChecklist
        steps={[
          {
            title: 'Clone and configure .env',
            body: (
              <p>
                <code>cp .env.example .env</code> — placeholder <code>SEAL_API_KEY</code> is fine with{' '}
                <code>SEAL_DEV_MODE=true</code>. <code>make up</code> fails fast if the key is
                missing.
              </p>
            ),
            code: `git clone ${SITE.github}.git
cd seal
cp .env.example .env
make up`,
          },
          {
            title: 'Seed analytics data & workspace schema',
            body: (
              <p>
                <code>make seed</code> loads sample tables (<code>products</code>,{' '}
                <code>orders</code>, <code>events_hourly</code>, …). Apply workspace tables once per
                fresh database.
              </p>
            ),
            code: `make seed
docker compose exec -T postgres psql -U postgres -d seal < scripts/migrate_app.sql
make sync-catalog`,
          },
          {
            title: 'Verify the API',
            body: <p>Health should return <code>{'"status":"ok"'}</code>. Catalog should list tables.</p>,
            code: fullLocalVerifySnippet(),
          },
          {
            title: 'Open the dashboard (optional)',
            body: (
              <p>
                Live console on port <strong>3001</strong> — Query, Chat (SSE), Catalog, Settings,
                Vector. See <Link href="/docs/dashboard">Dashboard</Link>.
              </p>
            ),
            code: 'cd apps/web && pnpm install && pnpm dev',
          },
        ]}
      />

      <SetupDoneBanner />

      <DocsProse>
        <div className="not-prose mt-10 flex flex-wrap gap-3">
          <Link href="/docs/integration-guide" className={cn(buttonVariants(), 'no-underline')}>
            Integration guide
          </Link>
          <Link
            href="/docs/features"
            className={cn(buttonVariants({ variant: 'outline' }), 'no-underline')}
          >
            All features
          </Link>
        </div>

        <h2 className="mt-12">Next reads</h2>
        <ul>
          <li>
            <Link href="/docs/workspace">Workspace settings</Link> — guardrails and limits in Postgres
          </li>
          <li>
            <Link href="/docs/guardrails">Guardrails</Link> — scope gate before SQL/RAG
          </li>
          <li>
            <Link href="/docs/chat-qa">Chat &amp; Q&A</Link> — sessions, streaming, charts
          </li>
          <li>
            <Link href="/docs/testing">Testing &amp; CI</Link> — <code>make check</code> and{' '}
            <code>make check-e2e</code>
          </li>
        </ul>
      </DocsProse>
    </div>
  );
}
