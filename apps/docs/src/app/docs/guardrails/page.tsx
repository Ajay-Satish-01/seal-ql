import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { Callout } from '@/components/docs/callout';
import { CodeBlock } from '@/components/code-block';
import { ConfigReference } from '@/components/docs/config-reference';
import { DocsProse } from '@/components/docs/docs-prose';
import { guardrailsConfig } from '@/data/configuration-reference';

export default function GuardrailsPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Guardrails"
        description="How Seal decides whether a message belongs on a data analytics API — before SQL, RAG, or multi-step chat models run."
      />

      <DocsProse>
        <p>
          Guardrails answer a single product question: <em>should this request use our database and LLM
          stack?</em> Seal is optimized for schema-aware analytics, not general chat. The scope gate
          runs on every <code>POST /v1/query</code> and <code>POST /v1/chat</code> so off-topic,
          abusive, or oversized prompts do not trigger SQL generation, vector retrieval, or expensive
          multi-model chat turns.
        </p>
        <p>
          Implementation lives in <code>packages/core/seal_core/guardrails/</code>. The API routes
          call <code>classify_scope</code>; chat additionally records results in{' '}
          <code>metadata.scope</code> (<code>ScopeMetadata</code> in OpenAPI) on every response.
        </p>

        <Callout variant="info" title="Different HTTP semantics by design">
          <strong>Chat</strong> returns HTTP <strong>200</strong> with a polite refusal — clients that
          only handle success codes still get a safe message. <strong>Query</strong> returns HTTP{' '}
          <strong>400</strong> with a structured <code>detail</code> object (code{' '}
          <code>query_out_of_scope</code>, <code>reason</code>, and up to three{' '}
          <code>suggested_queries</code>) — appropriate for programmatic agents that should treat
          scope failure as a hard error.
        </Callout>

        <h2>Classification pipeline</h2>
        <p>
          Stages run in order; an early exit skips later work (and often skips an LLM call entirely).
        </p>
        <pre className="not-prose overflow-x-auto rounded-xl border border-border/50 bg-muted/30 p-5 font-mono text-xs leading-relaxed text-foreground">
          {`User message
    │
    ▼
[1] GUARDRAILS_ENABLED?  ──no──▶ in_scope (source: disabled)
    │
    yes
    ▼
[2] Character limit      ──over──▶ out_of_scope (source: limits)
    │
    ok
    ▼
[3] Heuristics           ──match──▶ in_scope OR out_of_scope (source: heuristic)
    │
    inconclusive
    ▼
[4] LLM ScopeDecision    ──▶ in_scope OR out_of_scope (source: llm)
         │
         └── on error: fail-closed → out_of_scope if GUARDRAILS_FAIL_CLOSED`}
        </pre>

        <h3>Stage 1 — Master switch</h3>
        <p>
          When <code>GUARDRAILS_ENABLED=false</code>, classification returns in-scope immediately.
          Use only in isolated tests; production should leave guardrails on.
        </p>

        <h3>Stage 2 — Input limits</h3>
        <p>
          Hard caps before any model call: <code>MAX_QUERY_CHARS</code> for{' '}
          <code>/v1/query</code>, <code>MAX_CHAT_MESSAGE_CHARS</code> for the latest user message on
          chat. Chat history overrides must also fit <code>MAX_CHAT_HISTORY_CHARS</code> (enforced when
          you pass <code>messages</code> in the request body).
        </p>

        <h3>Stage 3 — Heuristics</h3>
        <p>
          Fast keyword detection (e.g. <code>sql</code>, <code>table</code>, <code>chart</code>) marks
          obvious data questions in-scope. Regex patterns catch common off-topic requests (creative
          writing, trivia) and injection phrases. When heuristics are confident,{' '}
          <code>metadata.scope.source</code> is <code>heuristic</code> — no classifier LLM runs.
        </p>

        <h3>Stage 4 — LLM classifier</h3>
        <p>
          Ambiguous text goes to a small Instructor call with <code>SCOPE_CLASSIFY_SYSTEM</code>. The
          model returns <code>ScopeDecision</code>: boolean <code>in_scope</code>, short{' '}
          <code>reason</code>, optional <code>category</code> (<code>data</code>,{' '}
          <code>off_topic</code>, <code>abuse</code>, <code>ambiguous</code>), and{' '}
          <code>confidence</code>.
        </p>
        <p>
          If the provider errors and <code>GUARDRAILS_FAIL_CLOSED=true</code> (default), the message
          is rejected. With fail-closed off, errors allow the request through — useful only when
          debugging provider connectivity.
        </p>

        <h2>What happens after classification</h2>
        <h3>Query — out of scope</h3>
        <p>
          The route raises HTTP 400 before introspection or planner work. No SQL, no chart, no token
          spend on <code>QueryPlan</code>. The body includes heuristic{' '}
          <code>suggested_queries</code> (no extra classifier LLM on this path).
        </p>
        <h3>Chat — out of scope</h3>
        <p>
          <code>ChatService</code> calls <code>_refusal_turn</code>: one LLM with{' '}
          <code>REFUSAL_SYSTEM</code> produces a short <code>ChatAnswer</code> (optional{' '}
          <code>suggested_queries</code>). Metadata and SSE <code>seal.meta</code> include{' '}
          <code>suggested_queries</code> (LLM when provided, otherwise heuristics). There is no{' '}
          <code>ChatDecision</code>, no <code>execute_natural_language_query</code>, and vector RAG
          enhancers see <code>in_scope=false</code> and stay disabled.
        </p>
        <h3>Chat — in scope</h3>
        <p>
          The normal turn runs: decision model → optional SQL pipeline → answer model (or stream).
          Guardrails do not guarantee SQL runs — <code>ChatDecision.needs_data</code> controls that.
        </p>

        <h2>In scope vs out of scope (examples)</h2>
        <div className="not-prose my-6 grid gap-4 sm:grid-cols-2">
          <div className="border-border/50 rounded-xl border p-4">
            <h3 className="text-foreground mb-2 font-semibold">In scope</h3>
            <ul className="text-muted-foreground list-disc space-y-1 pl-5 text-sm">
              <li>Revenue by month, top customers, row counts</li>
              <li>What tables exist? Describe the orders schema</li>
              <li>Metrics defined in the data catalog</li>
            </ul>
          </div>
          <div className="border-border/50 rounded-xl border p-4">
            <h3 className="text-foreground mb-2 font-semibold">Out of scope</h3>
            <ul className="text-muted-foreground list-disc space-y-1 pl-5 text-sm">
              <li>Poems, trivia, unrelated coding homework</li>
              <li>&quot;Ignore previous instructions…&quot;</li>
              <li>Messages over configured character limits</li>
            </ul>
          </div>
        </div>

        <h2>Configuration</h2>
        <p>
          Environment variables below can be overridden from{' '}
          <Link href="/docs/workspace">workspace settings</Link> (hot-reload in dev). Full reference:{' '}
          <Link href="/docs/configuration#guardrails">Configuration — Guardrails</Link>.
        </p>
        <ConfigReference rows={guardrailsConfig} />

        <h2>Other chat protections</h2>
        <ul>
          <li>
            <code>system</code> role in client-supplied <code>messages</code> overrides is rejected
            (HTTP 400) to reduce prompt injection via history.
          </li>
          <li>
            <code>include_charts=true</code> does not bypass scope or the decision step — charts only
            appear when SQL ran and chart generation applies.
          </li>
        </ul>

        <h2>Examples</h2>
        <p>Requires <code>SEAL_API_KEY</code> in your shell when auth is enabled.</p>
        <CodeBlock
          language="bash"
          code={`# Out-of-scope query → 400 with suggested_queries
curl -s -X POST http://localhost:8000/v1/query \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: $SEAL_API_KEY" \\
  -d '{"query":"Write me a poem about the ocean"}' | jq '.detail'

# Out-of-scope chat → 200 refusal (metadata.scope + suggested_queries)
curl -s -X POST http://localhost:8000/v1/chat \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: $SEAL_API_KEY" \\
  -d '{"message":"What is the capital of France?"}' | jq '{scope: .metadata.scope, suggested: .metadata.suggested_queries}'`}
        />

        <p>
          Full pipeline context: <Link href="/docs/how-it-works">How Seal works</Link> · Dashboard
          toggles on port 3001 (<Link href="/docs/dashboard">Dashboard</Link>).
        </p>
      </DocsProse>
    </div>
  );
}
