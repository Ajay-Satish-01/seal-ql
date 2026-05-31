import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { Callout } from '@/components/docs/callout';

export default function DashboardPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Operational dashboard"
        description="Live API console at apps/web (port 3001) for Query, Chat, Catalog, Settings, and Vector."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <p>
          The docs site (<code>apps/docs</code>, port <strong>3000</strong>) documents Seal and hosts a
          fixture-based <Link href="/demo">interactive demo</Link>. The{' '}
          <strong>dashboard</strong> is a separate Next.js app that calls your running API with the
          TypeScript SDK — no static fixtures.
        </p>

        <Callout variant="info" title="Start the dashboard">
          <pre className="not-prose overflow-x-auto rounded-md bg-muted/50 p-3 text-sm">
            {`cd apps/web && pnpm install && pnpm dev`}
          </pre>
          <p className="mt-2 mb-0">
            Open <a href="http://localhost:3001">http://localhost:3001</a>. Set API URL and{' '}
            <code>X-API-Key</code> in the connection bar (persisted in versioned localStorage).
          </p>
        </Callout>

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
              <td>Natural language → SQL, results, Vega-Lite chart</td>
            </tr>
            <tr>
              <td>
                <code>/chat</code>
              </td>
              <td>
                <code>POST /v1/chat</code> (SSE)
              </td>
              <td>Streaming chat with session memory and optional charts</td>
            </tr>
            <tr>
              <td>
                <code>/catalog</code>
              </td>
              <td>
                <code>GET /v1/catalog</code>, <code>PATCH /v1/catalog/descriptions</code>
              </td>
              <td>
                Edit descriptions (stored in Postgres); sync YAML from DB schema
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
              <td>Rebuild vector index when <code>VECTOR_STORE</code> is enabled</td>
            </tr>
          </tbody>
        </table>

        <h2 className="text-foreground mt-10 text-2xl font-bold">CORS & auth</h2>
        <p>
          Include <code>http://localhost:3001</code> in <code>CORS_ORIGINS</code> (default in{' '}
          <code>.env.example</code>). When <code>SEAL_API_KEY</code> is set, paste the same key in the
          connection bar. PATCH routes (workspace settings, catalog descriptions) require CORS{' '}
          <code>PATCH</code> — enabled on the API.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Configuration storage</h2>
        <p>
          Dashboard changes are stored in <strong>Postgres</strong> (
          <code>seal_app.workspace_kv</code>) when <code>WORKSPACE_STORE=postgres</code> (default).
          If the database has no override for a key, the API falls back to{' '}
          <code>config/workspace.json</code>, then to <strong>.env</strong> defaults.
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
