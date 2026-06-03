import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { Callout } from '@/components/docs/callout';
import { DocLink } from '@/components/docs/doc-link';
import { DocsProse } from '@/components/docs/docs-prose';

export default function EmbeddingPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Embedding Seal"
        description="How to run Seal as an internal capability layer behind your app, agent, or API gateway — responsibilities, deployment patterns, and safety boundaries."
      />

      <DocsProse>
        <p>
          Seal is open source so you can self-host natural-language analytics without rebuilding
          guardrails, SQL validation, or chart generation. This page is for{' '}
          <strong>integrators</strong> — not end users of a finished BI product. You run the Docker
          image (or source stack), call <code>/v1/query</code> and <code>/v1/chat</code> from your
          backend, and own everything around identity, tenancy, and UX.
        </p>

        <Callout variant="info" title="Start here if you are new">
          <Link href="/docs/integration-guide">Integration guide</Link> (Docker + SDK) ·{' '}
          <Link href="/docs/authentication">Authentication</Link> (BFF pattern) ·{' '}
          <Link href="/docs/multi-database">Multi-database routing</Link> (optional second backend)
        </Callout>

        <h2>What you build vs what Seal provides</h2>
        <div className="not-prose overflow-x-auto">
          <table className="border-border/50 my-6 w-full border-collapse border text-left text-sm">
            <thead className="bg-muted/80">
              <tr>
                <th className="border-border/50 border p-2">Your application</th>
                <th className="border-border/50 border p-2">Seal</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground">
              <tr>
                <td className="border-border/50 border p-2">User login, RBAC, tenant isolation</td>
                <td className="border-border/50 border p-2">
                  Shared <code>X-API-Key</code> on <code>/v1/*</code>
                </td>
              </tr>
              <tr>
                <td className="border-border/50 border p-2">
                  Product UI, saved questions, billing
                </td>
                <td className="border-border/50 border p-2">
                  NL → validated SQL, rows, Vega-Lite charts, optional chat sessions
                </td>
              </tr>
              <tr>
                <td className="border-border/50 border p-2">
                  Choosing which DB a tenant may query
                </td>
                <td className="border-border/50 border p-2">
                  <code>database_id</code> routing to pre-registered backends (ids only, never URLs
                  in JSON)
                </td>
              </tr>
              <tr>
                <td className="border-border/50 border p-2">
                  Rate limits and audit for your users
                </td>
                <td className="border-border/50 border p-2">
                  Scope guardrails, SQLGlot AST policy, read-only execution
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p>
          Never put <code>SEAL_API_KEY</code> in a browser or mobile app. Your server (or agent
          runtime with a secret store) calls Seal — same pattern as{' '}
          <Link href="/docs/authentication">Authentication</Link>.
        </p>

        <h2>Deployment patterns</h2>
        <ul>
          <li>
            <strong>One Seal, one database</strong> — Only <code>DATABASE_URL</code>; every request
            uses id <code>&quot;default&quot;</code>.
          </li>
          <li>
            <strong>One Seal, multiple databases</strong> — Add <code>config/databases.yaml</code>{' '}
            or <code>SEAL_DATABASES</code>; pass <code>database_id</code> on query, chat, and
            schema. See <Link href="/docs/multi-database">Multi-database routing</Link>.
          </li>
          <li>
            <strong>One Seal per tenant database</strong> — Strongest isolation; separate compose
            stack or namespace per customer.
          </li>
          <li>
            <strong>BFF / API gateway</strong> — Clients use your JWT; your API forwards to Seal
            with <code>X-API-Key</code> and the right <code>database_id</code> for that tenant.
          </li>
        </ul>
        <pre className="not-prose border-border/50 bg-muted/30 text-foreground overflow-x-auto rounded-xl border p-5 font-mono text-xs leading-relaxed">
          {`[Browser / mobile]  ──your JWT──►  [Your API]  ──X-API-Key──►  [Seal]  ──SQL──►  [DB]`}
        </pre>

        <h2>Three boundaries to understand</h2>
        <p>
          Embedding safely means knowing three layers. They run in order and fail independently:
        </p>

        <h3>1. Scope (guardrails)</h3>
        <p>
          <em>Should we spend tokens on SQL and RAG for this message?</em> Runs on every query and
          chat turn. In-scope: analytics and schema/catalog questions. Out-of-scope query → HTTP{' '}
          <strong>400</strong> with a nested <code>detail</code> object (fields inside{' '}
          <code>detail.detail</code>, <code>detail.reason</code>,{' '}
          <code>detail.suggested_queries</code>
          ). Out-of-scope chat → HTTP <strong>200</strong> refusal with the same suggestions in{' '}
          <code>metadata</code> (and on SSE <code>seal.meta</code>).
        </p>
        <CodeBlock
          language="json"
          code={`{
  "detail": {
    "detail": "query_out_of_scope",
    "reason": "off-topic pattern",
    "suggested_queries": [
      "Show order count by month",
      "What tables are available?"
    ]
  }
}`}
        />
        <p>
          <Link href="/docs/guardrails">Guardrails</Link> · Handle <code>QueryOutOfScopeError</code>{' '}
          in SDKs (parses the nested shape automatically)
        </p>

        <h3>2. SQL (zero-trust)</h3>
        <p>
          <em>Is this statement safe to execute?</em> Every generated query is parsed with SQLGlot,
          validated against live schema, sanitized, and limited before Postgres or DuckDB sees it.
          Same path for <code>/v1/query</code> and chat turns that run SQL.
        </p>
        <p>
          <Link href="/docs/zero-trust-sql">Zero-trust SQL</Link>
        </p>

        <h3>3. Enhancement and vector RAG</h3>
        <p>
          <em>What context is injected before the planner?</em> Chat runs an enhancement chain
          (schema focus, optional vector search, multi-turn summaries). <code>POST /v1/query</code>{' '}
          does <strong>not</strong> use this chain. Set <code>VECTOR_STORE=none</code> to run
          without embeddings; chat still works.
        </p>
        <p>
          <Link href="/docs/prompt-enhancement">Prompt enhancement</Link> ·{' '}
          <Link href="/docs/vector-rag">Vector RAG</Link>
        </p>

        <pre className="not-prose border-border/50 bg-muted/30 text-foreground overflow-x-auto rounded-xl border p-4 font-mono text-xs leading-relaxed">
          {`Request
  → guardrails (scope)
  → (chat only) enhancement + optional RAG
  → planner → SQLGlot → execute → answer / chart`}
        </pre>

        <h2>database_id, catalog, and sessions</h2>
        <p>
          When you register more than one backend, clients pass <code>database_id</code> on{' '}
          <code>/v1/query</code>, <code>/v1/chat</code>, and <code>GET /v1/schema</code>. Unknown
          ids return HTTP <strong>404</strong>. Responses include <code>metadata.database_id</code>{' '}
          (and execution stats when SQL runs) — see{' '}
          <DocLink href="/docs/execution-metadata">Execution metadata</DocLink>.
        </p>
        <Callout variant="warning" title="Shared catalog and RAG">
          The data catalog, semantic layer, and vector index are built from the <code>default</code>{' '}
          database only today. Non-default ids still run SQL against their backend but skip
          catalog/semantic injection and vector RAG. Chat sessions <strong>pin</strong>{' '}
          <code>database_id</code> after a successful in-scope turn; repeat the same id on
          follow-ups or start a new <code>session_id</code>.
        </Callout>

        <h2>Agents and HTTP tools</h2>
        <p>
          Ship OpenAI-compatible tools from{' '}
          <a href="/seal-tools.openai.json" className="text-primary hover:underline">
            seal-tools.openai.json
          </a>
          . Tools: <code>seal_get_schema</code>, <code>seal_get_catalog</code>,{' '}
          <code>seal_query</code>, <code>seal_chat</code>. <code>seal_get_catalog</code> reads the
          global catalog (default DB). <code>seal_get_schema</code>, <code>seal_query</code>, and{' '}
          <code>seal_chat</code> accept optional <code>database_id</code>. Parse structured 400s on
          out-of-scope queries (nested <code>detail</code> as above).
        </p>
        <p>
          <Link href="/docs/agent-frameworks">Agent frameworks</Link>
        </p>

        <h2>Verify locally</h2>
        <ol>
          <li>
            <code>make up &amp;&amp; make seed</code> — API on port 8000
          </li>
          <li>
            Docs site (this page): port <strong>3000</strong>
          </li>
          <li>
            <Link href="/docs/dashboard">Operational dashboard</Link> on port <strong>3001</strong>{' '}
            — database dropdown, Query/Chat/Schema against a live API
          </li>
          <li>
            <Link href="/demo">Interactive demo</Link> — fixture responses without the API
          </li>
        </ol>

        <h2>Roadmap for future work</h2>
        <ul>
          <li>Per-database catalog YAML</li>
          <li>Per-database vector indexes</li>
          <li>Per-database semantic registries</li>
        </ul>
        <p className="text-muted-foreground text-sm">
          Contributor mirror: <code>docs/embedding.md</code> in the repository.
        </p>
      </DocsProse>
    </div>
  );
}
