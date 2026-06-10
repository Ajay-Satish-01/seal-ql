import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { Callout } from '@/components/docs/callout';
import { DocLink } from '@/components/docs/doc-link';
import { DocsProse } from '@/components/docs/docs-prose';

export default function HowItWorksPage() {
  return (
    <div className="w-full">
      <PageHeader
        title="How Seal works"
        description="End-to-end flow from HTTP request to guardrails, LLM calls, validated SQL, and answers — for query and chat."
      />

      <DocsProse>
        <p>
          Seal is not a single LLM prompt. It is a <strong>pipeline</strong> of bounded steps: classify
          intent, optionally enrich context, plan SQL with structured outputs, validate through SQLGlot,
          execute with limits, then generate a user-facing answer or chart. Each step has explicit
          failure modes so operators can reason about cost, latency, and safety.
        </p>
        <p>
          All model calls go through <strong>LiteLLM</strong> with <strong>Instructor</strong> for
          structured JSON (scope decisions, chat decisions, SQL plans, chat answers). The active model
          is <code>LLM_MODEL</code> in LiteLLM <code>provider/model</code> form — see{' '}
          <Link href="/docs/configuration">Configuration reference</Link> and{' '}
          <Link href="/docs/self-hosting#llm-configuration">LLM configuration</Link>.
        </p>

        <h2>Two entry points</h2>
        <p>
          <strong><code>POST /v1/query</code></strong> is stateless analytics: one natural-language
          question in, SQL + rows + Vega-Lite chart out. There is no session memory and no enhancement
          chain — only guardrails, introspection, planner, validation, execution, and chart generation.
          Optional <code>database_id</code> selects a registered backend (default{' '}
          <code>&quot;default&quot;</code> from <code>DATABASE_URL</code>).
        </p>
        <p>
          <strong><code>POST /v1/chat</code></strong> is conversational: server-side{' '}
          <code>session_id</code>, optional SSE streaming, optional charts, optional{' '}
          <code>database_id</code>, and the default{' '}
          <strong>enhancement chain</strong> (schema focus, vector RAG, multi-turn context) on system
          prompts before decision and answer models run.
        </p>
        <p>
          <Link href="/docs/embedding">Embedding Seal</Link> — responsibility split, BFF pattern, and
          the three safety boundaries for integrators.{' '}
          <Link href="/docs/multi-database">Multi-database routing</Link> explains registry config,
          shared catalog limits, and <code>database_id</code> session pinning.
        </p>

        <h2>Guardrails (scope gate)</h2>
        <p>
          Every query and chat turn starts with <code>classify_scope</code> in{' '}
          <code>packages/core/seal_core/guardrails/</code>. The gate answers one question:{' '}
          <em>should this API spend tokens on SQL and RAG for this message?</em>
        </p>
        <ol>
          <li>
            <strong>Input limits</strong> — Compare length to <code>MAX_QUERY_CHARS</code> or{' '}
            <code>MAX_CHAT_MESSAGE_CHARS</code>. Over-limit requests stop immediately with source{' '}
            <code>limits</code> (no LLM).
          </li>
          <li>
            <strong>Heuristics</strong> — Regex and keyword checks for obvious data questions vs
            off-topic or injection patterns. Returns <code>source: heuristic</code> when confident.
          </li>
          <li>
            <strong>LLM classifier</strong> — When heuristics are inconclusive, a small Instructor call
            returns <code>ScopeDecision</code> (<code>in_scope</code>, <code>reason</code>,{' '}
            <code>category</code>, <code>confidence</code>).
          </li>
          <li>
            <strong>Fail-closed</strong> — If the classifier errors and{' '}
            <code>GUARDRAILS_FAIL_CLOSED=true</code>, the message is treated as out-of-scope.
          </li>
        </ol>
        <p>
          <strong>Out-of-scope query</strong> → HTTP 400, structured <code>detail</code> (
          <code>query_out_of_scope</code>, <code>reason</code>, <code>suggested_queries</code>), no
          planner. <strong>Out-of-scope chat</strong> → HTTP 200 with a short refusal from{' '}
          <code>REFUSAL_SYSTEM</code> only — no <code>ChatDecision</code>, no SQL, no RAG. Metadata
          includes <code>scope</code>, <code>refusal: true</code>, and <code>database_id</code> (session
          is not pinned on refusal).
        </p>
        <p>
          Deeper detail: <Link href="/docs/guardrails">Guardrails</Link> · contributor doc{' '}
          <code>docs/guardrails.md</code>.
        </p>

        <h2>Query path</h2>
        <p className="text-muted-foreground text-sm leading-relaxed">
          Unlike chat, query <strong>introspects schema before</strong> <code>classify_scope</code>{' '}
          so table-name hints can inform the scope gate.
        </p>
        <pre className="not-prose overflow-x-auto rounded-xl border border-border/50 bg-muted/30 p-5 font-mono text-xs leading-relaxed text-foreground">
          {`POST /v1/query
    │
    ├─ resolve database_id → registry
    │     └─ unknown → HTTP 404 unknown_database_id
    │
    ├─ introspect schema (chosen backend)
    ├─ classify_scope (channel=query, uses table hints from schema)
    │     └─ out of scope → HTTP 400 structured query_out_of_scope
    │
    ├─ ReasoningOrchestrator.run_pre (clarification)
    │     └─ clarification_required → message + empty sql, no execution
    │
    ├─ execute_natural_language_query (shared pipeline)
    │     ├─ planner.generate_plan → QueryPlan (LLM + Instructor)
    │     ├─ SQLValidator (schema: tables / columns)
    │     ├─ SQLSanitizer (read-only AST, LIMIT, complexity)
    │     ├─ executor.execute
    │     └─ repair loop (feed DB/validation errors back to planner, up to 3 attempts)
    │
    ├─ ChartEngine.generate → Vega-Lite spec (heuristic, not an LLM)
    └─ ReasoningOrchestrator.run_post (follow-ups, research notes)`}
        </pre>
        <p>
          You should expect one primary planner LLM call per attempt, plus extra calls only when SQL
          validation or the database returns a repairable error. Charts are derived from the plan and
          result shape — not from a separate chart LLM.
        </p>
        <p>
          SQL validation and sanitization are documented in{' '}
          <Link href="/docs/zero-trust-sql">Zero-trust SQL boundary</Link>.
        </p>

        <h2>Chat path (after guardrails)</h2>
        <pre className="not-prose overflow-x-auto rounded-xl border border-border/50 bg-muted/30 p-5 font-mono text-xs leading-relaxed text-foreground">
          {`POST /v1/chat
    │
    ├─ resolve database_id → registry (404 if unknown)
    ├─ session store (session_id, TTL, database_id pin check)
    ├─ classify_scope (channel=chat)
    │     └─ out of scope → refusal LLM only → 200 + metadata.scope
    │
    ├─ ReasoningOrchestrator.run_pre (clarification, inferred context)
    │     └─ clarification_required → early return, no SQL
    │
    ├─ ChatDecision LLM (needs_data true/false)
    │     └─ enhance_system_prompt (stage=decision)
    │
    ├─ if needs_data:
    │     ├─ ContextRetriever.select_tables (catalog + schema, no LLM)
    │     └─ execute_natural_language_query (same pipeline as /v1/query)
    │           optional ChartEngine when include_charts=true
    │
    ├─ ReasoningOrchestrator.run_post (chat skips heuristic follow-up layers)
    ├─ enhance_system_prompt (stage=answer)
    └─ Answer LLM (ChatAnswer or streamed tokens + enrichment)
          └─ follow-ups / research notes from answer LLM (not query post layers)
          └─ recent history + SQL preview rows in prompt`}
        </pre>
        <p>
          <code>needs_data=false</code> skips SQL entirely — useful for &quot;what does this column
          mean?&quot; when schema/catalog context is enough. <code>include_charts</code> does not skip
          guardrails or the decision step; charts appear only when SQL ran successfully and chart
          generation applies.
        </p>

        <h2>Layered reasoning (chat + query)</h2>
        <p>
          <code>ReasoningOrchestrator</code> adds optional product-intelligence layers controlled by{' '}
          <code>REASONING_*</code> env vars (see{' '}
          <Link href="/docs/configuration#reasoning">Configuration → Layered reasoning</Link> and{' '}
          <Link href="/docs/reasoning">Layered reasoning</Link> for the full guide). Outputs
          appear in assistant text and <code>metadata.reasoning</code> (flat on SSE{' '}
          <code>seal.meta</code>).
        </p>
        <ul>
          <li>
            <strong>Pre-execution</strong> — clarifying questions when input is ambiguous; chat-only
            inferred context from prior turns.
          </li>
          <li>
            <strong>Post-execution (query)</strong> — heuristic follow-ups and research notes after
            SQL. <strong>Chat</strong> uses the answer LLM for those fields instead of post layers.
          </li>
          <li>
            <code>REASONING_ANALYSIS_FOLLOWUPS_ENABLED</code> and{' '}
            <code>REASONING_RESEARCH_NOTES_ENABLED</code> affect query post layers only; chat
            follow-ups and research notes still come from the answer LLM.
          </li>
          <li>
            When <code>clarification_required</code> is true, chat returns early without SQL; query
            returns <code>message</code> with empty <code>sql</code>.
          </li>
        </ul>

        <h2>Prompt enhancement (chat only)</h2>
        <p>
          When <code>CHAT_ENHANCEMENT_ENABLED=true</code> and the request is in scope,{' '}
          <code>EnhancementOrchestrator</code> runs a chain before selected LLM stages:
        </p>
        <ol>
          <li>
            <strong>SchemaAwareEnhancer</strong> — Focused tables (up to{' '}
            <code>CHAT_MAX_CONTEXT_TABLES</code>), FK hints, catalog descriptions from global YAML +
            workspace overrides.
          </li>
          <li>
            <strong>VectorRagEnhancer</strong> — Embeds the user message, searches{' '}
            <code>VECTOR_STORE</code>, appends top-K chunks. Disabled when out-of-scope, store is{' '}
            <code>none</code>, or message is too short.
          </li>
          <li>
            <strong>MultiTurnEnhancer</strong> — Optional conversation summary in the system prompt;
            <code>ChatService</code> keeps the last three user turns at decision and{' '}
            <code>CHAT_RECENT_MESSAGES</code> at the answer stage.
          </li>
        </ol>
        <p>
          <code>ChatService</code> calls <code>enhance_system_prompt</code> at decision and answer
          stages. <code>enhance_user_messages</code> is part of the enhancer protocol for custom and
          orchestrator use. Enhancers <strong>fail open</strong>: exceptions log a warning and the
          base prompt is used. Custom enhancers append via <code>SEAL_ENHANCERS</code>.
        </p>
        <p>
          <Link href="/docs/prompt-enhancement">Prompt enhancement</Link> ·{' '}
          <code>docs/chat-enhancement.md</code>
        </p>

        <h2>LLM calls per path (typical in-scope turn)</h2>
        <div className="not-prose border-border/50 my-6 overflow-x-auto rounded-xl border text-sm">
          <table className="w-full min-w-[36rem] text-left">
            <thead>
              <tr className="border-border/50 bg-muted/40 border-b">
                <th className="text-foreground px-4 py-3 font-semibold">Step</th>
                <th className="text-foreground px-4 py-3 font-semibold">/v1/query</th>
                <th className="text-foreground px-4 py-3 font-semibold">/v1/chat</th>
                <th className="text-foreground px-4 py-3 font-semibold">Structured output</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground divide-border/40 divide-y">
              <tr>
                <td className="px-4 py-2">Scope gate</td>
                <td className="px-4 py-2">0–1 (if heuristics inconclusive)</td>
                <td className="px-4 py-2">0–1</td>
                <td className="px-4 py-2 font-mono text-xs">ScopeDecision</td>
              </tr>
              <tr>
                <td className="px-4 py-2">Chat decision</td>
                <td className="px-4 py-2">—</td>
                <td className="px-4 py-2">1</td>
                <td className="px-4 py-2 font-mono text-xs">ChatDecision</td>
              </tr>
              <tr>
                <td className="px-4 py-2">SQL planner (+ repair)</td>
                <td className="px-4 py-2">1–3</td>
                <td className="px-4 py-2">0–3 if needs_data</td>
                <td className="px-4 py-2 font-mono text-xs">QueryPlan</td>
              </tr>
              <tr>
                <td className="px-4 py-2">Refusal</td>
                <td className="px-4 py-2">—</td>
                <td className="px-4 py-2">1 if out of scope</td>
                <td className="px-4 py-2 font-mono text-xs">ChatAnswer</td>
              </tr>
              <tr>
                <td className="px-4 py-2">Final answer</td>
                <td className="px-4 py-2">—</td>
                <td className="px-4 py-2">1 (or streamed text)</td>
                <td className="px-4 py-2 font-mono text-xs">ChatAnswer / tokens</td>
              </tr>
              <tr>
                <td className="px-4 py-2">Vector embed (RAG)</td>
                <td className="px-4 py-2">—</td>
                <td className="px-4 py-2">0–1 if Chroma enabled</td>
                <td className="px-4 py-2">Embedding API via LiteLLM</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p>
          Heuristic scope matches skip the classifier LLM entirely — you will see{' '}
          <code>metadata.scope.source: heuristic</code> in chat responses.
        </p>

        <h2>SQL safety (zero trust)</h2>
        <p>
          No LLM output runs on the database without passing <code>packages/sql</code>: AST parse,
          dialect rules, join/depth limits from settings, and sanitization that enforces{' '}
          <code>MAX_ROWS</code> and blocks destructive statements. This applies equally to query and
          chat SQL paths because both call <code>execute_natural_language_query</code>.
        </p>

        <h2>Data catalog role</h2>
        <p>
          The catalog is <strong>global</strong>: one YAML file (plus workspace description overrides)
          feeds the planner, chat retriever, and optional vector index. Auto-sync rebuilds structure
          from DDL; operator descriptions survive sync when stored in workspace. See{' '}
          <Link href="/docs/data-catalog">Data catalog</Link>.
        </p>

        <h2>Streaming (chat)</h2>
        <p>
          With <code>stream=true</code>, the API emits <code>event: seal.meta</code> first (flat JSON:
          session, sql, results, columns, chart, execution fields, enhancement, scope), then
          OpenAI-style token deltas, then <code>[DONE]</code>. Refusals still stream as a single
          content delta after meta. See{' '}
          <DocLink href="/docs/execution-metadata">Execution metadata</DocLink> and{' '}
          <DocLink href="/docs/chat-streaming">SSE streaming</DocLink>.
        </p>

        <Callout variant="info" title="Where to tune behavior">
          Environment variables: <Link href="/docs/configuration">Configuration reference</Link>.
          Runtime overrides: <Link href="/docs/workspace">Workspace settings</Link>. Product
          architecture diagram: <Link href="/docs/architecture">System architecture</Link>.
        </Callout>
      </DocsProse>
    </div>
  );
}
