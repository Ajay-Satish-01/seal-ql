import { PageHeader } from '@/components/page-header';
import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import Link from 'next/link';
import {
  ArrowRight,
  Database,
  Shield,
  Zap,
  BarChart,
  KeyRound,
  MessageSquare,
  Layers,
  Settings2,
  FolderCog,
  TestTube2,
  LineChart,
  FileJson,
  SlidersHorizontal,
} from 'lucide-react';
import { DocsProse } from '@/components/docs/docs-prose';
import { PortsTable } from '@/components/docs/ports-table';
import { Callout } from '@/components/docs/callout';

const CAPABILITY_CARDS = [
  {
    icon: MessageSquare,
    title: 'Chat & Q&A',
    desc: 'Multi-turn /v1/chat with session memory, optional charts, SSE streaming, and a shared SQL pipeline with /v1/query.',
    href: '/docs/chat-qa',
  },
  {
    icon: FileJson,
    title: 'Data catalog',
    desc: 'Auto-synced catalog.yaml from live DDL; business descriptions in Postgres via workspace.',
    href: '/docs/data-catalog',
  },
  {
    icon: Layers,
    title: 'Prompt enhancement',
    desc: 'Schema context, multi-turn summaries, optional Chroma vector RAG before SQL generation.',
    href: '/docs/prompt-enhancement',
  },
  {
    icon: Shield,
    title: 'Guardrails',
    desc: 'Heuristics + LLM scope gate — refuse off-topic chat (200) or reject queries (400).',
    href: '/docs/guardrails',
  },
  {
    icon: Settings2,
    title: 'How it works',
    desc: 'Guardrails, LLM stages, SQL pipeline, and chat enhancement — end to end.',
    href: '/docs/how-it-works',
  },
  {
    icon: SlidersHorizontal,
    title: 'Configuration',
    desc: 'Every .env variable — purpose, defaults, and what you should see when it works.',
    href: '/docs/configuration',
  },
  {
    icon: FolderCog,
    title: 'Workspace',
    desc: 'Persist settings and catalog overrides in Postgres; hot-reload in dev, Apply in prod.',
    href: '/docs/workspace',
  },
  {
    icon: Zap,
    title: 'Auto-repair SQL',
    desc: 'Planner repair loop when the database returns column or syntax errors.',
    href: '/docs/features#planner',
  },
  {
    icon: Database,
    title: 'Zero-trust SQL',
    desc: 'SQLGlot AST validation blocks destructive SQL and enforces LIMIT on selects.',
    href: '/docs/features#sql-safety',
  },
  {
    icon: LineChart,
    title: 'Vega-Lite charts',
    desc: 'Every /v1/query response includes a chart spec; optional on chat via include_charts.',
    href: '/docs/charts-analysis',
  },
  {
    icon: KeyRound,
    title: 'API key auth',
    desc: 'X-API-Key on /v1/*; BFF pattern — your backend holds the secret, not browsers.',
    href: '/docs/authentication',
  },
  {
    icon: TestTube2,
    title: 'Testing & CI',
    desc: 'Unit tests with mocks plus live E2E on every PR — make check and make check-e2e locally.',
    href: '/docs/testing',
  },
] as const;

export default function DocsPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="What is Seal?"
        description="An open-source AI SQL gateway: natural language → validated SQL → results and Vega-Lite charts."
      />

      <DocsProse>
        <p className="text-lg">
          Seal sits between your LLM and your database. It introspects schema, enriches prompts with a
          data catalog, classifies scope with guardrails, generates SQL through a structured planner,
          validates every statement with SQLGlot, executes read-only queries, and returns chart-ready
          Vega-Lite specs — via REST and Python/TypeScript SDKs.
        </p>

        <Callout variant="success" title="Start here">
          New users: <Link href="/docs/quickstart">Quickstart</Link> (Docker + SDK). Contributors:{' '}
          <Link href="/docs/contributing">Contributing</Link> (<code>make up</code>). Try the{' '}
          <Link href="/demo">interactive demo</Link> without running the API.
        </Callout>

        <h2>Local ports</h2>
        <PortsTable />

        <h2>Core capabilities</h2>
      </DocsProse>

      <div className="not-prose mt-6 mb-10 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {CAPABILITY_CARDS.map(({ icon: Icon, title, desc, href }) => (
          <Link
            key={href}
            href={href}
            className="border-border/50 bg-card/60 hover:border-primary/40 group rounded-xl border p-5 shadow-sm transition-colors"
          >
            <Icon className="text-primary mb-3 h-7 w-7 transition-transform group-hover:scale-105" />
            <h4 className="text-foreground mb-1.5 font-semibold">{title}</h4>
            <p className="text-muted-foreground text-sm leading-relaxed">{desc}</p>
          </Link>
        ))}
      </div>

      <DocsProse>
        <h2>How a query flows</h2>
        <pre className="not-prose overflow-x-auto rounded-xl border border-border/50 bg-muted/30 p-4 font-mono text-xs leading-relaxed text-foreground">
          {`Client (SDK / dashboard / curl)
    → POST /v1/query or /v1/chat
    → Guardrails (limits + scope)
    → Enhancement (schema + optional vector RAG)
    → LiteLLM + Instructor planner
    → SQLGlot AST validation
    → Postgres / DuckDB executor
    → Results + Vega-Lite chart`}
        </pre>
        <p>
          Details: <Link href="/docs/architecture">Architecture</Link> ·{' '}
          <Link href="/docs/api-reference">API reference</Link>.
        </p>

        <h2>Deployment modes</h2>
        <ul>
          <li>
            <strong>Docker image</strong> — <code>seal/api:latest</code> on Hub; compose with Postgres
            and optional Ollama (<Link href="/docs/self-hosting">Self-hosting</Link>).
          </li>
          <li>
            <strong>Source dev</strong> — <code>make up</code>, <code>make seed</code>, dashboard on
            3001, this docs site on 3000.
          </li>
          <li>
            <strong>SDK integration</strong> — <code>pip install seal</code> / <code>npm install seal</code>{' '}
            from your app server (<Link href="/docs/integration-guide">Integration guide</Link>).
          </li>
        </ul>

        <div className="not-prose mt-10 flex flex-wrap gap-4">
          <Link href="/docs/quickstart" className={cn(buttonVariants({ size: 'lg' }), 'rounded-sm')}>
            Quickstart <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
          <Link href="/demo" className={cn(buttonVariants({ variant: 'outline', size: 'lg' }), 'rounded-sm')}>
            Interactive demo
          </Link>
        </div>
      </DocsProse>
    </div>
  );
}
