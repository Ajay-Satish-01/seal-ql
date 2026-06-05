import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { Callout } from '@/components/docs/callout';

export default function DashboardPage() {
  return (
    <div className="w-full">
      <PageHeader
        title="Operational dashboard"
        description="Live API console at apps/web (port 3001) for Query, Chat, Schema, Catalog, Settings, and Vector."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <p>
          The docs site (<code>apps/docs</code>, port <strong>3000</strong>) documents Seal and hosts a
          fixture-based <Link href="/demo">interactive demo</Link>. The{' '}
          <strong>dashboard</strong> is a separate Next.js app that calls your running API — no static
          fixtures.
        </p>

        <Callout variant="info" title="Start the dashboard">
          <pre className="not-prose overflow-x-auto rounded-md bg-muted/50 p-3 text-sm">
            {`cd apps/web && pnpm install && pnpm dev`}
          </pre>
          <p className="mt-2 mb-0">
            Open <a href="http://localhost:3001">http://localhost:3001</a>. Set API URL and{' '}
            <code>X-API-Key</code> in the connection bar (persisted in versioned localStorage). Click{' '}
            <strong>Connect</strong> to load registered databases from <code>GET /v1/databases</code>.
          </p>
        </Callout>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Multi-database routing</h2>
        <p>
          When the API is configured with extra backends (
          <code>SEAL_DATABASES_PATH</code> or <code>SEAL_DATABASES</code>), the connection bar shows a{' '}
          <strong>Database</strong> dropdown. The selected id is sent as <code>database_id</code> on
          Query, Chat, and Schema requests and stored in localStorage between visits.
        </p>
        <ul>
          <li>
            <strong>Query</strong> — <code>POST /v1/query</code> with <code>database_id</code>; shows
            full <code>metadata</code> (row count, timing, warnings, <code>used_sql</code>).
          </li>
          <li>
            <strong>Chat</strong> — SSE <code>seal.meta</code> before token deltas; metadata panel
            (enhancement, <code>scope.source</code>, refusal, <code>sql_error</code>). Invalid meta
            shows a toast but keeps partial session fields when possible. Same <code>database_id</code>{' '}
            on every turn; changing the dropdown clears the session. See{' '}
            <Link href="/docs/execution-metadata">Execution metadata</Link>.
          </li>
          <li>
            <strong>Schema</strong> — <code>GET /v1/schema?database_id=…</code> for live DDL on the
            selected backend.
          </li>
          <li>
            <strong>Catalog &amp; Vector</strong> — still global (default database catalog); a banner
            warns when a non-default database is selected.
          </li>
        </ul>
        <p>
          Full setup and limitations:{' '}
          <Link href="/docs/multi-database">Multi-database routing</Link>. Embedder architecture:{' '}
          <Link href="/docs/embedding">Embedding Seal</Link>.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Pages</h2>
        <table>
          <thead>
            <tr>
              <th>Route</th>
              <th>API</th>
              <th>Purpose</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <code>/query</code>
              </td>
              <td>
                <code>POST /v1/query</code>
              </td>
              <td>Natural language → SQL, results, Vega-Lite chart (per database_id)</td>
            </tr>
            <tr>
              <td>
                <code>/chat</code>
              </td>
              <td>
                <code>POST /v1/chat</code> (SSE)
              </td>
              <td>Streaming chat with session memory, database_id on every turn</td>
            </tr>
            <tr>
              <td>
                <code>/schema</code>
              </td>
              <td>
                <code>GET /v1/schema</code>
              </td>
              <td>Introspect tables/columns for the selected database_id</td>
            </tr>
            <tr>
              <td>
                <code>/catalog</code>
              </td>
              <td>
                <code>GET /v1/catalog</code>, <code>PATCH /v1/catalog/descriptions</code>
              </td>
              <td>
                Edit descriptions (stored in Postgres); sync YAML from default DB schema
              </td>
            </tr>
            <tr>
              <td>
                <code>/settings</code>
              </td>
              <td>
                <code>GET/PATCH /v1/workspace/settings</code>
              </td>
              <td>
                Guardrails, limits — saved to DB; hot-reload on save in dev,{' '}
                <strong>Apply to API</strong> in prod
              </td>
            </tr>
            <tr>
              <td>
                <code>/vector</code>
              </td>
              <td>
                <code>POST /v1/vector/reindex</code>
              </td>
              <td>Rebuild vector index (default DB catalog) when <code>VECTOR_STORE</code> is enabled</td>
            </tr>
          </tbody>
        </table>

        <h2 className="text-foreground mt-10 text-2xl font-bold">CORS & auth</h2>
        <p>
          Include <code>http://localhost:3001</code> in <code>CORS_ORIGINS</code> (default in{' '}
          <code>.env.example</code>). Paste the same <code>SEAL_API_KEY</code> from your API{' '}
          <code>.env</code> into the connection bar. PATCH routes (workspace settings, catalog
          descriptions) require CORS <code>PATCH</code> — enabled on the API.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Configuration storage</h2>
        <p>
          Dashboard changes are stored in <strong>Postgres</strong> (
          <code>seal_app.workspace_kv</code>) when <code>WORKSPACE_STORE=postgres</code> (default).
          If the database has no override for a key, the API falls back to{' '}
          <code>config/workspace.json</code>, then to <strong>.env</strong> defaults.
        </p>
        <p>
          Additional SQL backends are <strong>not</strong> configured from the dashboard — set{' '}
          <code>SEAL_DATABASES_PATH</code> or <code>SEAL_DATABASES</code> in <code>.env</code> and
          restart the API. After restart, click <strong>Connect</strong> to refresh the database list.
        </p>
        <p>
          Catalog <strong>descriptions</strong> edited in the dashboard are stored in the workspace DB.
          The YAML file (<code>config/catalog.yaml</code>) is regenerated on schema sync; descriptions
          are re-applied from the DB after sync. See{' '}
          <Link href="/docs/data-catalog">Data catalog</Link> and repository{' '}
          <code>docs/workspace-api.md</code>.
        </p>
        <p>
          Guardrails keys are editable from Settings — see{' '}
          <Link href="/docs/guardrails">Guardrails</Link>.
        </p>
      </div>
    </div>
  );
}
