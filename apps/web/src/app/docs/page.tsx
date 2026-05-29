import { PageHeader } from '@/components/page-header';
import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import Link from 'next/link';
import { ArrowRight, Database, Shield, Zap, BarChart } from 'lucide-react';

export default function DocsPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="What is Intelligence Connector?"
        description="A unified, secure, and intelligent gateway between Natural Language and your Databases."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <p className="text-lg">
          Intelligence Connector is a comprehensive SDK and API gateway designed to streamline and
          secure natural language database querying for modern AI applications. It serves as the
          critical safety and translation layer between your LLMs and your relational databases.
        </p>

        <h3 className="text-foreground mt-8 mb-4 text-xl font-semibold">
          Why use Intelligence Connector?
        </h3>
        <p>
          Building reliable text-to-SQL applications is notoriously difficult. Developers face
          hallucinated schemas, destructive SQL injections (`DROP TABLE`), malformed syntax, and a
          lack of visual data representation. Intelligence Connector solves these problems
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
            <BarChart className="text-primary mb-3 h-8 w-8" />
            <h4 className="mb-2 text-lg font-semibold">Instant Visualization</h4>
            <p className="text-muted-foreground text-sm">
              Every executed query returns a fully-typed Vega-Lite JSON specification, allowing your
              frontend to instantly render beautiful, dynamic charts without manual processing.
            </p>
          </div>
        </div>

        <p>
          Whether you are building an internal analytics copilot or a customer-facing data
          dashboard, Intelligence Connector provides the SDKs and APIs to get to production safely.
        </p>

        <div className="not-prose mt-10 flex gap-4">
          <Link
            href="/docs/features"
            className={cn(buttonVariants({ variant: 'outline', size: 'lg' }), 'rounded-full')}
          >
            Explore Features
          </Link>
          <Link
            href="/docs/quickstart"
            className={cn(buttonVariants({ size: 'lg' }), 'rounded-full')}
          >
            Quickstart <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
