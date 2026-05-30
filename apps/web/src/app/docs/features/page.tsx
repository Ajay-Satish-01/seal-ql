import Link from 'next/link';
import { PageHeader } from '@/components/page-header';

export default function FeaturesPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Features"
        description="Deep dive into the core capabilities of Seal."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <h2>Schema Introspection</h2>
        <p>
          Before any query is generated, the system actively fetches the live DDL (Data Definition
          Language) of your connected database. Instead of blindly guessing table structures,
          Seal feeds the exact tables, column types, and foreign key relationships
          into the LLM context.
        </p>
        <ul>
          <li>
            <strong>Supported Dialects:</strong> Postgres, DuckDB, TimescaleDB.
          </li>
          <li>
            <strong>Dynamic Updates:</strong> Schema changes are instantly recognized without manual
            mapping.
          </li>
          <li>
            <strong>Token Optimization:</strong> Only relevant tables (based on semantic search) are
            injected to reduce latency and token costs.
          </li>
        </ul>

        <hr />

        <h2>Agent Planner & Auto-Repair</h2>
        <p>
          The Query Planner is the brain of the system. Powered by <code>Instructor</code>, it
          forces the LLM to output highly-structured, verifiable JSON rather than free-text SQL.
        </p>
        <p>
          If the LLM makes a mistake (e.g., querying a non-existent column or a syntax error), the
          executor catches the database exception and feeds it back to the planner. The agent
          automatically enters a <strong>repair loop</strong>, re-evaluating its logic based on the
          error, and trying again—all transparently to the user.
        </p>

        <hr />

        <h2>Zero-Trust SQL AST Validation (SQLGlot)</h2>
        <p>
          Never trust LLM output. Before any generated SQL touches your database, it passes through
          a strict validation boundary using <code>SQLGlot</code>.
        </p>
        <ul>
          <li>
            <strong>Destructive Operation Blocking:</strong> <code>DROP</code>, <code>DELETE</code>,{' '}
            <code>TRUNCATE</code>, <code>ALTER</code>, and <code>UPDATE</code> statements are
            aggressively rejected.
          </li>
          <li>
            <strong>AST Parsing:</strong> We parse the query into an Abstract Syntax Tree to ensure
            it&apos;s structurally valid and semantically safe.
          </li>
          <li>
            <strong>Mandatory Pagination:</strong> Unbounded <code>SELECT *</code> queries are
            automatically modified to include a <code>LIMIT</code> to prevent memory exhaustion.
          </li>
        </ul>

        <hr />

        <h2>API authentication</h2>
        <p>
          Self-hosted deployments protect <code>/v1/query</code> and <code>/v1/schema</code> with a
          shared <code>X-API-Key</code> header. Production settings require a generated secret (
          <code>SEAL_AUTH_REQUIRED=true</code>, <code>SEAL_DEV_MODE=false</code>), reject
          placeholder keys even if dev mode was left on, optionally hide public Swagger (
          <code>SEAL_DISABLE_DOCS</code>), and expect your application server — not end-user
          browsers — to hold the key. See the{' '}
          <Link href="/docs/authentication" className="text-primary">
            Authentication
          </Link>{' '}
          guide for BFF patterns, Docker env vars, and SDK usage.
        </p>

        <hr />

        <h2>Instant Chart Generation</h2>
        <p>
          Data without visualization is hard to consume. Seal includes a Chart
          Engine that analyzes the returned SQL result set and automatically generates a complete{' '}
          <strong>Vega-Lite</strong> JSON specification.
        </p>
        <p>
          Whether the result is a time-series aggregation, a categorical breakdown, or a simple
          metric, the engine selects the optimal visualization type (Line, Bar, Area, Pie) and maps
          the axes dynamically.
        </p>
      </div>
    </div>
  );
}
