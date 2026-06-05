import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { DocsProse } from '@/components/docs/docs-prose';
import { Callout } from '@/components/docs/callout';

export default function ArchitecturePage() {
  return (
    <div className="w-full">
      <PageHeader
        title="System architecture"
        description="How natural language becomes validated SQL, results, and charts."
      />

      <DocsProse>
        <p>
          Seal is a FastAPI application (<code>apps/api</code>) orchestrating core packages: planner,
          chat, catalog, enhancement, guardrails, workspace, SQL validation, and chart generation.
        </p>

        <h2>Request pipeline</h2>
        <pre className="not-prose overflow-x-auto rounded-xl border border-border/50 bg-muted/30 p-5 font-mono text-xs leading-relaxed text-foreground">
          {`┌─────────────┐     ┌──────────────────────────────────────────────────┐
│ SDK / curl  │────▶│ FastAPI  /v1/query  |  /v1/chat  |  /v1/catalog  …   │
│ Dashboard   │     └───────────────────────────┬──────────────────────────┘
└─────────────┘                                 │
                    ┌───────────────────────────▼───────────────────────────┐
                    │ Auth (X-API-Key) · input size limits                    │
                    └───────────────────────────┬───────────────────────────┘
                                                │
                    ┌───────────────────────────▼───────────────────────────┐
                    │ Guardrails — heuristics + LLM ScopeDecision             │
                    └───────────────────────────┬───────────────────────────┘
                                                │ in scope
                    ┌───────────────────────────▼───────────────────────────┐
                    │ Enhancement — schema context · vector RAG · history     │
                    │ Data catalog (YAML + workspace description overrides)   │
                    └───────────────────────────┬───────────────────────────┘
                                                │
                    ┌───────────────────────────▼───────────────────────────┐
                    │ Planner — LiteLLM + Instructor (structured SQL plan)    │
                    └───────────────────────────┬───────────────────────────┘
                                                │
                    ┌───────────────────────────▼───────────────────────────┐
                    │ SQLGlot AST validator (packages/sql) — zero trust       │
                    └───────────────────────────┬───────────────────────────┘
                                                │
                    ┌───────────────────────────▼───────────────────────────┐
                    │ Executor — Postgres / TimescaleDB / DuckDB              │
                    └───────────────────────────┬───────────────────────────┘
                                                │
                    ┌───────────────────────────▼───────────────────────────┐
                    │ Chart engine → Vega-Lite spec + rows + metadata         │
                    └─────────────────────────────────────────────────────────┘`}
        </pre>

        <h2>Configuration storage</h2>
        <p>Effective operator settings merge three layers (see <Link href="/docs/workspace">Workspace</Link>):</p>
        <ol>
          <li>
            <code>.env</code> / process environment — base defaults
          </li>
          <li>
            <code>config/workspace.json</code> — read fallback when Postgres is empty
          </li>
          <li>
            <code>seal_app.workspace_kv</code> — primary writes from dashboard/API
          </li>
        </ol>
        <p>
          Catalog <strong>structure</strong> lives in <code>config/catalog.yaml</code> (regenerated on
          sync). <strong>Descriptions</strong> edited in the dashboard live in workspace storage and
          are re-applied after each sync.
        </p>

        <h2>Chat vs query</h2>
        <div className="not-prose border-border/50 my-6 overflow-x-auto rounded-xl border text-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="border-border/50 bg-muted/40 border-b">
                <th className="text-foreground px-4 py-3 font-semibold">Aspect</th>
                <th className="text-foreground px-4 py-3 font-semibold">POST /v1/query</th>
                <th className="text-foreground px-4 py-3 font-semibold">POST /v1/chat</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground divide-border/40 divide-y">
              <tr>
                <td className="px-4 py-2">Session</td>
                <td className="px-4 py-2">Stateless per request</td>
                <td className="px-4 py-2">session_id + server-side memory</td>
              </tr>
              <tr>
                <td className="px-4 py-2">Charts</td>
                <td className="px-4 py-2">Always included</td>
                <td className="px-4 py-2">Optional (include_charts)</td>
              </tr>
              <tr>
                <td className="px-4 py-2">Streaming</td>
                <td className="px-4 py-2">JSON response</td>
                <td className="px-4 py-2">Optional SSE (stream=true)</td>
              </tr>
              <tr>
                <td className="px-4 py-2">Out of scope</td>
                <td className="px-4 py-2">HTTP 400</td>
                <td className="px-4 py-2">HTTP 200 refusal</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2>Deployment topology</h2>
        <ul>
          <li>
            <strong>API container</strong> — Uvicorn, mounts <code>config/</code>, connects to Postgres
          </li>
          <li>
            <strong>Postgres</strong> — analytics data + <code>seal_app</code> workspace schema
          </li>
          <li>
            <strong>Ollama</strong> (optional) — local models when <code>OLLAMA_PROFILE=default</code>
          </li>
          <li>
            <strong>Chroma</strong> (optional) — vector index when <code>VECTOR_STORE=chroma</code>
          </li>
        </ul>

        <Callout variant="info" title="Frontends are separate">
          This docs site (<code>apps/docs</code>, port 3000) uses fixture data for /demo. The{' '}
          <Link href="/docs/dashboard">dashboard</Link> (port 3001) calls your live API. Neither is
          embedded in the API container.
        </Callout>

        <h2>LLM and guardrails</h2>
        <p>
          Guardrails run first on every query and chat turn. Chat may invoke several structured LLM
          calls (scope, decision, planner repairs, answer) plus optional embeddings for RAG. Query
          typically uses scope + planner (+ repairs) only. See{' '}
          <Link href="/docs/how-it-works">How Seal works</Link> for stage-by-stage detail and an LLM
          call inventory, and <Link href="/docs/guardrails">Guardrails</Link> for classification
          behavior.
        </p>

        <p>
          Deeper dives: <Link href="/docs/how-it-works">How it works</Link> ·{' '}
          <Link href="/docs/features">Features</Link> ·{' '}
          <Link href="/docs/api-reference">API reference</Link> ·{' '}
          <Link href="/docs/self-hosting">Self-hosting</Link>.
        </p>
      </DocsProse>
    </div>
  );
}
