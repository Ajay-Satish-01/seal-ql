import { PageHeader } from '@/components/page-header';
import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import Link from 'next/link';
import { ArrowRight, Database, Shield, Zap, BarChart, KeyRound, MessageSquare } from 'lucide-react';

export default function DocsPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="What is Seal?"
        description="A unified, secure, and intelligent gateway between Natural Language and your Databases."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <p className="text-lg">
          Seal is a comprehensive SDK and API gateway designed to streamline and
          secure natural language database querying for modern AI applications. It serves as the
          critical safety and translation layer between your LLMs and your relational databases.
        </p>

        <h3 className="text-foreground mt-8 mb-4 text-xl font-semibold">
          Why use Seal?
        </h3>
        <p>
          Building reliable text-to-SQL applications is notoriously difficult. Developers face
          hallucinated schemas, destructive SQL injections (`DROP TABLE`), malformed syntax, and a
          lack of visual data representation. Seal solves these problems
          systematically:
        </p>

        <div className="not-prose mt-8 mb-8 grid grid-cols-1 gap-6 md:grid-cols-2">
          <div className="border-border/50 bg-card text-card-foreground rounded-xl border p-5 shadow-sm">
            <Shield className="text-primary mb-3 h-8 w-8" />
            <h4 className="mb-2 text-lg font-semibold">Zero-Trust Safety</h4>
            <p className="text-muted-foreground text-sm">
              Every generated SQL query is parsed into an AST via SQLGlot. Destructive operations
              (DROP, DELETE) are explicitly blocked before they ever touch the database.
            </p>
          </div>
          <div className="border-border/50 bg-card text-card-foreground rounded-xl border p-5 shadow-sm">
            <Zap className="text-primary mb-3 h-8 w-8" />
            <h4 className="mb-2 text-lg font-semibold">Auto-Repair Loop</h4>
            <p className="text-muted-foreground text-sm">
              If an LLM hallucinates a bad column or syntax, the gateway captures the database
              exception and dynamically re-prompts the LLM to repair the query automatically.
            </p>
          </div>
          <div className="border-border/50 bg-card text-card-foreground rounded-xl border p-5 shadow-sm">
            <Database className="text-primary mb-3 h-8 w-8" />
            <h4 className="mb-2 text-lg font-semibold">Schema Introspection</h4>
            <p className="text-muted-foreground text-sm">
              We actively fetch your database schema (Postgres, DuckDB) and inject only the relevant
              DDL and Semantic Models into the LLM context to save tokens and improve accuracy.
            </p>
          </div>
          <div className="border-border/50 bg-card text-card-foreground rounded-xl border p-5 shadow-sm">
            <MessageSquare className="text-primary mb-3 h-8 w-8" />
            <h4 className="mb-2 text-lg font-semibold">Chat &amp; Q&A</h4>
            <p className="text-muted-foreground text-sm">
              Multi-turn <code>/v1/chat</code> with session memory, optional charts, SSE streaming,
              and a global data catalog for business context — no external agent framework required.
            </p>
          </div>
          <div className="border-border/50 bg-card text-card-foreground rounded-xl border p-5 shadow-sm">
            <BarChart className="text-primary mb-3 h-8 w-8" />
            <h4 className="mb-2 text-lg font-semibold">Instant Visualization</h4>
            <p className="text-muted-foreground text-sm">
              Every executed query returns a fully-typed Vega-Lite JSON specification, allowing your
              frontend to instantly render beautiful, dynamic charts without manual processing.
            </p>
          </div>
          <div className="border-border/50 bg-card text-card-foreground rounded-xl border p-5 shadow-sm md:col-span-2">
            <KeyRound className="text-primary mb-3 h-8 w-8" />
            <h4 className="mb-2 text-lg font-semibold">API authentication</h4>
            <p className="text-muted-foreground text-sm">
              Self-host with <code>SEAL_API_KEY</code> and <code>X-API-Key</code>. Production uses{' '}
              <code>SEAL_AUTH_REQUIRED</code>, <code>SEAL_DEV_MODE=false</code>, and optional{' '}
              <code>SEAL_DISABLE_DOCS</code>. End users should call your backend, not hold the shared
              key — see{' '}
              <Link href="/docs/authentication" className="text-primary">
                Authentication
              </Link>
              .
            </p>
          </div>
        </div>

        <p>
          Whether you are building an internal analytics copilot or a customer-facing data
          dashboard, Seal provides the SDKs and APIs to get to production safely.
        </p>

        <p className="mt-8 rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 text-sm">
          <strong className="text-foreground">No clone required.</strong> Pull the Docker image,
          install the SDK, and point at your API. See{' '}
          <Link href="/docs/quickstart" className="text-primary">
            Quickstart
          </Link>{' '}
          or try the{' '}
          <Link href="/demo" className="text-primary">
            interactive demo
          </Link>{' '}
          first.
        </p>

        <div className="not-prose mt-10 flex flex-wrap gap-4">
          <Link href="/demo" className={cn(buttonVariants({ size: 'lg' }), 'rounded-sm')}>
            Interactive Demo
          </Link>
          <Link
            href="/docs/quickstart"
            className={cn(buttonVariants({ variant: 'outline', size: 'lg' }), 'rounded-sm')}
          >
            Quickstart <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
