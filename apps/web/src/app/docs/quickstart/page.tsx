import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';

export default function QuickstartPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Quickstart & Installation"
        description="Get your local environment running in minutes."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none text-lg leading-relaxed">
        <h2 className="text-foreground mt-10 mb-4 text-2xl font-bold">Prerequisites</h2>
        <ul className="mb-8 list-disc space-y-2 pl-6">
          <li>Docker & Docker Compose</li>
          <li>
            <code>uv</code> (Python package installer)
          </li>
          <li>
            <code>pnpm</code> (Node package manager)
          </li>
        </ul>

        <h2 className="text-foreground mt-10 mb-4 text-2xl font-bold">1. Spin Up Dev Stack</h2>
        <p>
          Use the automated Makefile controls to orchestrate your local environment (API, Postgres,
          Ollama):
        </p>
        <CodeBlock code="make up" />

        <p className="mt-4">Once running, the stack exposes:</p>
        <ul className="mb-8 list-disc space-y-2 pl-6">
          <li>
            API Server: <code>http://localhost:8000</code>
          </li>
          <li>
            Postgres: <code>localhost:5432</code>
          </li>
          <li>
            Ollama: <code>http://localhost:11434</code>
          </li>
        </ul>

        <h2 className="text-foreground mt-10 mb-4 text-2xl font-bold">2. Populate Database Seed</h2>
        <p>Seed Postgres with a production-grade analytics schema to test introspection:</p>
        <CodeBlock code="make seed" />
      </div>
    </div>
  );
}
