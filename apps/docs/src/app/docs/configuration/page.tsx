import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { Callout } from '@/components/docs/callout';
import { ConfigSection } from '@/components/docs/config-reference';
import { DocsProse } from '@/components/docs/docs-prose';
import { LlmConfigSection } from '@/components/docs/llm-config';
import {
  authConfig,
  catalogConfig,
  chatConfig,
  corsConfig,
  databaseConfig,
  guardrailsConfig,
  querySafetyConfig,
  vectorConfig,
} from '@/data/configuration-reference';

export default function ConfigurationPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Configuration reference"
        description="How environment variables shape API behavior, what each setting controls, and what you should see when it is working."
      />

      <DocsProse>
        <p>
          Seal is configured primarily through a <code>.env</code> file (or Compose environment
          blocks) loaded into <code>seal_core.settings.Settings</code> at API startup. A smaller
          subset can be overridden at runtime through{' '}
          <Link href="/docs/workspace">workspace settings</Link> when you use the dashboard or{' '}
          <code>PATCH /v1/workspace/settings</code>.
        </p>
        <p>
          Think of configuration in three layers: <strong>infrastructure</strong> (database URL,
          ports, CORS), <strong>product behavior</strong> (guardrails, chat enhancement, catalog sync),
          and <strong>operator overrides</strong> (workspace KV in Postgres). The tables below
          describe each environment variable&apos;s purpose and the behavior you should observe when
          the value is correct — not just its name and type.
        </p>

        <Callout variant="info" title="Source of truth">
          The repository ships <code>.env.example</code> with commented sections matching this
          page. Copy it to <code>.env</code> for local development; use secrets management in
          production instead of committing real keys.
        </Callout>

        <p>
          For how guardrails, LLM calls, SQL, and enhancement fit together, read{' '}
          <Link href="/docs/how-it-works">How Seal works</Link> first — this page focuses on
          individual knobs and expected outcomes.
        </p>

        <ConfigSection
          id="database"
          title="Database"
          intro={
            <>
              <p>
                The API needs a live SQL database for schema introspection, catalog generation, and
                query execution. Docker Compose wires <code>DATABASE_URL</code> to the bundled
                Timescale/Postgres service; self-hosted production often points at your own managed
                Postgres instead.
              </p>
              <p>
                To register additional backends (warehouse, DuckDB file, read replica), see{' '}
                <Link href="/docs/multi-database">Multi-database routing</Link> — a step-by-step guide
                with examples. Each request passes <code>database_id</code> (default{' '}
                <code>&quot;default&quot;</code>).
              </p>
              <p>
                After changing the URL, restart the API container. Workspace and catalog files do not
                move with the database — run <code>make seed</code> or your own migrations on the
                new instance.
              </p>
            </>
          }
          rows={databaseConfig}
        />

        <div className="not-prose">
          <LlmConfigSection />
        </div>

        <ConfigSection
          id="authentication"
          title="Authentication & API surface"
          intro={
            <>
              <p>
                Authentication is header-based: clients send <code>X-API-Key</code> when{' '}
                <code>SEAL_API_KEY</code> is defined. Development stacks relax validation so you can
                iterate quickly; production stacks should require a real key and disable embedded API
                documentation.
              </p>
              <p>
                See <Link href="/docs/authentication">Authentication</Link> for SDK examples and
                rotation guidance.
              </p>
            </>
          }
          rows={authConfig}
        />

        <ConfigSection
          id="catalog"
          title="Data catalog"
          intro={
            <>
              <p>
                The catalog is a <strong>global</strong> YAML registry shared by natural-language
                query and chat. It is regenerated from live DDL when auto-sync is enabled, while
                human-written table descriptions are stored in workspace Postgres and re-applied after
                each sync.
              </p>
              <p>
                Deeper workflow: <Link href="/docs/data-catalog">Data catalog</Link>.
              </p>
            </>
          }
          rows={catalogConfig}
        />

        <ConfigSection
          id="guardrails"
          title="Guardrails"
          intro={
            <>
              <p>
                Guardrails run before expensive LLM planner work. They enforce size limits, fast
                heuristics, and a structured scope classifier. Chat refusals are polite HTTP 200
                messages; query refusals are HTTP 400 with <code>query_out_of_scope</code>.
              </p>
              <p>
                Full pipeline and examples: <Link href="/docs/guardrails">Guardrails</Link>.
              </p>
            </>
          }
          rows={guardrailsConfig}
        />

        <ConfigSection
          id="chat"
          title="Chat & prompt enhancement"
          intro={
            <>
              <p>
                Chat sessions are server-side maps keyed by <code>session_id</code>. Enhancement
                controls how much schema, vector context, and history reach the models before SQL
                generation and the final answer.
              </p>
              <p>
                Enhancer chain details:{' '}
                <Link href="/docs/prompt-enhancement">Prompt enhancement</Link>.
              </p>
            </>
          }
          rows={chatConfig}
        />

        <ConfigSection
          id="query-safety"
          title="Query safety"
          intro={
            <>
              <p>
                Every generated statement passes through SQLGlot AST validation in{' '}
                <code>packages/sql</code> before execution. These limits add defense in depth so
                even a misbehaving model cannot issue unbounded scans or destructive statements.
              </p>
              <p>
                You will see validation errors in API responses (HTTP 400) rather than partial
                results when a query violates policy.
              </p>
            </>
          }
          rows={querySafetyConfig}
        />

        <ConfigSection
          id="vector"
          title="Vector RAG"
          intro={
            <>
              <p>
                Vector search is optional. The default image keeps <code>VECTOR_STORE=none</code> so
                deployments without embeddings stay lean. Enabling Chroma requires a rebuild with the
                Chroma extra and a persistent volume for index data.
              </p>
              <p>
                Operations guide: <Link href="/docs/vector-rag">Vector RAG</Link>.
              </p>
            </>
          }
          rows={vectorConfig}
        />

        <ConfigSection
          id="network"
          title="Network & ports"
          intro={
            <p>
              CORS applies to browser clients only. Server-side SDKs and curl are unaffected. Compose
              port variables document the local URL map (API 8000, docs 3000, dashboard 3001).
            </p>
          }
          rows={corsConfig}
        />

        <h2 className="text-foreground mt-12 text-2xl font-bold">Workspace vs environment</h2>
        <p>
          Keys such as <code>guardrails_enabled</code>, <code>llm_model</code>, and{' '}
          <code>rag_top_k</code> can be changed from the dashboard. Effective values merge{' '}
          <code>.env</code> → optional <code>config/workspace.json</code> → Postgres{' '}
          <code>seal_app.workspace_kv</code>. In development, many keys hot-reload immediately; in
          production, call <code>POST /v1/workspace/settings/apply</code> after PATCH.
        </p>
        <p>
          <Link href="/docs/workspace">Workspace settings</Link> explains precedence, storage, and
          apply semantics.
        </p>

        <h2 className="text-foreground mt-12 text-2xl font-bold">Applying changes</h2>
        <ul>
          <li>
            <strong>Environment variables</strong> — restart the API container (
            <code>docker compose up -d --force-recreate api</code> or <code>make up</code> from
            source).
          </li>
          <li>
            <strong>Workspace hot-reload keys</strong> — PATCH (+ apply in production); see workspace
            docs for <code>restart_required</code> vs <code>pending_apply</code>.
          </li>
          <li>
            <strong>Catalog YAML on disk</strong> — survives when <code>./config</code> is mounted;
            run catalog sync after DDL migrations.
          </li>
        </ul>
      </DocsProse>
    </div>
  );
}
