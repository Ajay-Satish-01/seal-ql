import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { Callout } from '@/components/docs/callout';
import { ConfigReference } from '@/components/docs/config-reference';
import { DocsProse } from '@/components/docs/docs-prose';
import { SITE } from '@/lib/constants';
import { curlWithAuth } from '@/lib/doc-snippets';

const workspaceRuntimeRows = [
  {
    name: 'WORKSPACE_STORE',
    type: 'string',
    default: 'postgres',
    description:
      'Selects whether settings and catalog overrides persist in Postgres (`seal_app.workspace_kv`) or only in `config/workspace.json`.',
    expect:
      'With `postgres`, dashboard edits survive API restarts and are shared across replicas. With `file`, you are in a single-node, test-style setup without the app schema migration.',
  },
  {
    name: 'SEAL_DEV_MODE',
    type: 'boolean',
    default: 'true (local)',
    description:
      'Controls whether PATCH immediately applies hot-reload keys to the in-process Settings object.',
    expect:
      'When true, guardrail toggles and limits take effect on the next request without an apply step. When false, the API stores changes but waits for `POST /v1/workspace/settings/apply` or a container restart for non-hot keys.',
  },
];

export default function WorkspacePage() {
  const base = SITE.defaultBaseUrl;

  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Workspace settings"
        description="Persist operator configuration — guardrails, limits, LLM model, and catalog descriptions — with clear precedence and apply semantics."
      />

      <DocsProse>
        <p>
          Not every tunable value belongs in a hand-edited <code>.env</code> file. Operators need to
          adjust guardrails, token limits, and catalog descriptions from the dashboard without
          redeploying containers. The <strong>workspace</strong> layer stores that operational
          state in Postgres (by default) while keeping structural catalog data in{' '}
          <code>config/catalog.yaml</code>.
        </p>
        <p>
          Workspace settings do <em>not</em> replace database migrations or table DDL. They change how
          the API <strong>behaves</strong> on top of an already-connected database — who is allowed
          to ask what, how large prompts may be, and how tables are described to the LLM.
        </p>

        <Callout variant="info" title="Effective value precedence">
          When the API resolves a setting, it walks this chain: base defaults from{' '}
          <code>.env</code> → optional read of <code>config/workspace.json</code> → rows in{' '}
          <code>seal_app.workspace_kv</code> (dashboard and API writes). The winning value is what
          you see in <code>GET /v1/workspace/settings</code> under <code>effective</code>.
        </Callout>

        <h2>Why three storage layers exist</h2>
        <p>
          <strong>Environment (`.env`)</strong> is the bootstrap contract: database URL, API keys,
          and defaults shipped with Compose. It is appropriate for secrets and infrastructure you
          never want checked into workspace JSON.
        </p>
        <p>
          <strong>File fallback (`config/workspace.json`)</strong> lets local tests and air-gapped
          setups run without Postgres app schema. The API may read this file when a key is missing
          in the database; it is not the primary write path when{' '}
          <code>WORKSPACE_STORE=postgres</code>.
        </p>
        <p>
          <strong>Postgres (`seal_app.workspace_kv`)</strong> is the source of truth for production.
          The dashboard Settings and Catalog pages write here. Run{' '}
          <code>scripts/migrate_app.sql</code> once per database (included in <code>make seed</code>{' '}
          flows) so the schema exists before the API starts.
        </p>

        <ConfigReference rows={workspaceRuntimeRows} />

        <h2>HTTP API</h2>
        <p>
          All workspace routes live under <code>/v1/workspace/*</code> and require{' '}
          <code>X-API-Key</code> when <code>SEAL_API_KEY</code> is set. A successful{' '}
          <code>GET /v1/workspace/settings</code> returns three useful views: the{' '}
          <code>effective</code> object you should treat as truth, a <code>schema</code> array
          describing each field&apos;s type and whether it hot-reloads, and <code>storage</code>{' '}
          metadata (postgres vs file, pending apply keys).
        </p>

        <div className="not-prose border-border/50 my-6 overflow-x-auto rounded-xl border text-sm">
          <table className="w-full min-w-[28rem] text-left">
            <thead>
              <tr className="border-border/50 bg-muted/40 border-b">
                <th className="text-foreground px-4 py-3 font-semibold">Method</th>
                <th className="text-foreground px-4 py-3 font-semibold">Path</th>
                <th className="text-foreground px-4 py-3 font-semibold">When to use it</th>
                <th className="text-foreground px-4 py-3 font-semibold">What to expect</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground divide-border/40 divide-y">
              <tr>
                <td className="px-4 py-2 font-mono">GET</td>
                <td className="px-4 py-2 font-mono">/v1/workspace/settings</td>
                <td className="px-4 py-2">Inspect effective config and field metadata</td>
                <td className="px-4 py-2">
                  JSON with <code>effective</code>, <code>schema</code>, <code>storage</code>; use
                  before debugging guardrail or LLM behavior
                </td>
              </tr>
              <tr>
                <td className="px-4 py-2 font-mono">PATCH</td>
                <td className="px-4 py-2 font-mono">/v1/workspace/settings</td>
                <td className="px-4 py-2">Change one or more keys from automation or GitOps</td>
                <td className="px-4 py-2">
                  Persists to Postgres; in dev, hot keys apply immediately; in prod, may populate{' '}
                  <code>pending_apply</code>
                </td>
              </tr>
              <tr>
                <td className="px-4 py-2 font-mono">POST</td>
                <td className="px-4 py-2 font-mono">/v1/workspace/settings/apply</td>
                <td className="px-4 py-2">Production apply after PATCH</td>
                <td className="px-4 py-2">
                  Running API picks up hot-reload keys without full restart; response lists what
                  changed
                </td>
              </tr>
              <tr>
                <td className="px-4 py-2 font-mono">GET</td>
                <td className="px-4 py-2 font-mono">/v1/workspace/export</td>
                <td className="px-4 py-2">Backup or drift detection</td>
                <td className="px-4 py-2">
                  Snapshot of effective settings plus catalog description overrides as JSON
                </td>
              </tr>
              <tr>
                <td className="px-4 py-2 font-mono">PATCH</td>
                <td className="px-4 py-2 font-mono">/v1/catalog/descriptions</td>
                <td className="px-4 py-2">Update table/view descriptions only</td>
                <td className="px-4 py-2">
                  Overrides stored in workspace; re-applied on next catalog sync — YAML alone is not
                  enough
                </td>
              </tr>
              <tr>
                <td className="px-4 py-2 font-mono">POST</td>
                <td className="px-4 py-2 font-mono">/v1/vector/reindex</td>
                <td className="px-4 py-2">After enabling Chroma or large catalog changes</td>
                <td className="px-4 py-2">
                  Background-style rebuild; chat RAG starts returning chunks only after index completes
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2>Hot reload vs restart</h2>
        <p>
          Each field in the workspace schema declares <code>hot_reload: true</code> or{' '}
          <code>false</code>. Hot fields (guardrails, character limits, <code>llm_model</code>, RAG
          top-k) can flow into the running process. Cold fields (for example{' '}
          <code>vector_store</code> and <code>cors_origins</code>) require a container restart because
          they change which subsystems are initialized at boot.
        </p>

        <div className="not-prose border-border/50 my-6 overflow-x-auto rounded-xl border text-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="border-border/50 bg-muted/40 border-b">
                <th className="text-foreground px-4 py-3 font-semibold">Mode</th>
                <th className="text-foreground px-4 py-3 font-semibold">PATCH behavior</th>
                <th className="text-foreground px-4 py-3 font-semibold">What you should do</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground divide-border/40 divide-y">
              <tr>
                <td className="px-4 py-2">
                  Dev (<code>SEAL_DEV_MODE=true</code>)
                </td>
                <td className="px-4 py-2">Persist + apply hot-reload keys immediately</td>
                <td className="px-4 py-2">
                  Change a limit in the dashboard, send a chat message — refusal or acceptance should
                  reflect the new value on the next request
                </td>
              </tr>
              <tr>
                <td className="px-4 py-2">
                  Prod (<code>SEAL_DEV_MODE=false</code>)
                </td>
                <td className="px-4 py-2">Persist only; hot keys listed in pending_apply</td>
                <td className="px-4 py-2">
                  Click <strong>Apply to API</strong> in the dashboard or call{' '}
                  <code>POST /v1/workspace/settings/apply</code> before validating behavior
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p>
          If <code>restart_required</code> is non-empty in the settings response, schedule an API
          restart — hot apply cannot switch vector backends or CORS policy.
        </p>

        <h2>Examples</h2>
        <p>
          The snippets below assume <code>SEAL_API_KEY</code> is exported in your shell (see{' '}
          <Link href="/docs/authentication">Authentication</Link>). Replace the base URL if your API
          is not on localhost.
        </p>
        <CodeBlock language="bash" code={curlWithAuth(base, 'GET', '/v1/workspace/settings')} />
        <CodeBlock
          language="bash"
          code={curlWithAuth(base, 'PATCH', '/v1/workspace/settings', {
            settings: { guardrails_enabled: true, max_query_chars: 4000 },
          })}
        />
        <CodeBlock language="bash" code={curlWithAuth(base, 'POST', '/v1/workspace/settings/apply')} />

        <h2>Dashboard</h2>
        <p>
          The operational dashboard on{' '}
          <Link href="/docs/dashboard">port 3001</Link> mirrors these APIs. Settings edits show a
          diff against effective values; Catalog edits write description overrides that sync merges
          back into <code>DATA_CATALOG_PATH</code>. Guardrail labels match{' '}
          <Link href="/docs/guardrails">Guardrails</Link>.
        </p>

        <h2>Catalog descriptions</h2>
        <p>
          Description overrides are workspace data, not manual YAML edits. After{' '}
          <code>POST /v1/catalog/sync</code>, the API rebuilds structure from DDL and reapplies your
          saved descriptions so planners see operator language (&quot;revenue&quot;,
          &quot;active users&quot;) instead of raw column names alone. See{' '}
          <Link href="/docs/data-catalog">Data catalog</Link> for the full sync workflow.
        </p>

        <p>
          Environment variables for the same keys are documented on the{' '}
          <Link href="/docs/configuration">Configuration reference</Link> page.
        </p>
      </DocsProse>
    </div>
  );
}
