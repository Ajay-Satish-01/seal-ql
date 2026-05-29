import { PageHeader } from '@/components/page-header';
import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

export default function DocsPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Introduction"
        description="Welcome to the Intelligence Connector documentation."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none text-lg leading-relaxed">
        <p>
          Intelligence Connector is an{' '}
          <strong>AI-powered SQL query generation, validation, and visualization SDK</strong>. It
          bridges the gap between natural language questions and secure, optimized database
          execution.
        </p>
        <p className="mt-4">
          By utilizing advanced schema introspection, strict AST validation via SQLGlot, and
          declarative semantic models, it provides a zero-trust environment for executing
          LLM-generated SQL against Postgres, TimescaleDB, and DuckDB.
        </p>

        <div className="mt-12">
          <Link
            href="/docs/quickstart"
            className={cn(buttonVariants({ size: 'lg' }), 'rounded-full')}
          >
            Proceed to Quickstart <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
