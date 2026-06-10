import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { Callout } from '@/components/docs/callout';
import { DocLink } from '@/components/docs/doc-link';
import { CodeBlock } from '@/components/code-block';
import { ConfigReference } from '@/components/docs/config-reference';
import { MetadataFieldList } from '@/components/docs/metadata-field-list';
import { MetadataJsonBlock } from '@/components/docs/metadata-json-block';
import { DocsProse } from '@/components/docs/docs-prose';
import { reasoningConfig } from '@/data/configuration-reference';
import {
  REASONING_FIELDS,
  CHAT_METADATA_CLARIFICATION_JSON,
} from '@/lib/execution-metadata';
import { SITE } from '@/lib/constants';

export default function ReasoningPage() {
  return (
    <div className="w-full">
      <PageHeader
        title="Layered reasoning"
        description="Clarifying questions, analytical follow-ups, research notes, and inferred context — on both /v1/query and /v1/chat."
      />

      <DocsProse>
        <p>
          When reasoning is enabled, Seal adds structured intelligence layers to query and chat
          responses. Instead of only returning SQL results, the API can ask clarifying questions when
          the input is ambiguous, suggest analytical follow-ups, surface data-backed research notes,
          and (chat only) infer context from prior conversation turns.
        </p>
        <p>
          All reasoning output appears in two places: the assistant-visible <code>message</code> text
          and structured <code>metadata.reasoning</code> (flat on SSE <code>seal.meta</code>).
          Consumers can use either or both — the structured fields are typed in the OpenAPI spec,
          both SDKs, and the shared TypeScript contract.
        </p>

        <Callout variant="info" title="Heuristic layers vs chat answer LLM">
          Built-in <strong>reasoning layers</strong> use fast keyword and schema heuristics — no
          extra LLM calls. <strong>Chat</strong> also runs an answer LLM (and optional stream
          enrichment) that populates <code>analysis_followups</code> and{' '}
          <code>research_notes</code>; those fields are not controlled by{' '}
          <code>REASONING_ANALYSIS_FOLLOWUPS_ENABLED</code> or{' '}
          <code>REASONING_RESEARCH_NOTES_ENABLED</code>. The{' '}
          <code>REASONING_LATENCY_BUDGET_MS</code> budget (default 500 ms) applies to heuristic
          layers only.
        </Callout>

        <h2>How it works</h2>
        <p>
          <code>ReasoningOrchestrator</code> in{' '}
          <code>packages/core/seal_core/reasoning/</code> runs pluggable layers in two phases:
        </p>
        <pre className="not-prose overflow-x-auto rounded-xl border border-border/50 bg-muted/30 p-5 font-mono text-xs leading-relaxed text-foreground">
          {`ReasoningOrchestrator
    ├─ PRE_EXECUTION
    │     ├─ InferredContextLayer  (chat only — prior-turn topics)
    │     └─ ClarificationLayer    (chat + query — ambiguous input)
    │
    └─ POST_EXECUTION
          ├─ AnalysisFollowupsLayer  (deeper analytical angles)
          └─ ResearchNotesLayer      (data-backed observations)`}
        </pre>
        <p>
          <strong>Chat</strong> runs <strong>pre-execution</strong> layers before SQL, then produces
          follow-ups and research notes via the <strong>answer LLM</strong> — post-execution heuristic
          layers are disabled on chat. <strong>Query</strong> is stateless — it skips{' '}
          <code>InferredContextLayer</code> (no session) and runs both pre- and post-execution layers
          around the shared SQL pipeline.
        </p>

        <h2>Layer reference</h2>
        <div className="not-prose border-border/50 my-6 overflow-x-auto rounded-xl border text-sm">
          <table className="w-full min-w-[36rem] text-left">
            <thead>
              <tr className="border-border/50 bg-muted/40 border-b">
                <th className="text-foreground px-4 py-3 font-semibold">Layer</th>
                <th className="text-foreground px-4 py-3 font-semibold">Chat</th>
                <th className="text-foreground px-4 py-3 font-semibold">Query</th>
                <th className="text-foreground px-4 py-3 font-semibold">Phase</th>
                <th className="text-foreground px-4 py-3 font-semibold">What it does</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground divide-border/40 divide-y">
              <tr>
                <td className="px-4 py-2 font-mono text-xs">inferred_context</td>
                <td className="px-4 py-2">Yes</td>
                <td className="px-4 py-2">No</td>
                <td className="px-4 py-2">Pre</td>
                <td className="px-4 py-2">
                  Extracts topics from previous assistant messages so the current turn benefits
                  from session memory without re-running retrieval.
                </td>
              </tr>
              <tr>
                <td className="px-4 py-2 font-mono text-xs">clarification</td>
                <td className="px-4 py-2">Yes</td>
                <td className="px-4 py-2">Yes</td>
                <td className="px-4 py-2">Pre</td>
                <td className="px-4 py-2">
                  When the user message is vague (no specific intent keyword, no table hint, large
                  schema), generates targeted requirement-gathering questions. Sets{' '}
                  <code>clarification_required: true</code>.
                </td>
              </tr>
              <tr>
                <td className="px-4 py-2 font-mono text-xs">analysis_followups</td>
                <td className="px-4 py-2">Answer LLM</td>
                <td className="px-4 py-2">Post layer</td>
                <td className="px-4 py-2">Post</td>
                <td className="px-4 py-2">
                  Chat: <code>ChatAnswer</code> / stream enrichment. Query: heuristic layer after SQL
                  (e.g. &quot;Break this down by segment&quot;).
                </td>
              </tr>
              <tr>
                <td className="px-4 py-2 font-mono text-xs">research_notes</td>
                <td className="px-4 py-2">Answer LLM</td>
                <td className="px-4 py-2">Post layer</td>
                <td className="px-4 py-2">Post</td>
                <td className="px-4 py-2">
                  Chat: answer LLM fields. Query: execution-backed heuristic notes. Trust-gated when{' '}
                  <code>SEAL_TRUST_EXPLAINABILITY_ENABLED=false</code>.
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2>Clarification flow</h2>
        <p>
          When <code>clarification_required</code> is true and <code>clarifying_questions</code> is
          non-empty, the API returns early <strong>before running SQL</strong>:
        </p>
        <ul>
          <li>
            <strong>Chat</strong> — HTTP 200 with a clarification message; <code>used_sql: false</code>;
            no <code>sql</code> or <code>results</code>.
          </li>
          <li>
            <strong>Query</strong> — HTTP 200 with top-level <code>message</code> containing the
            clarification text; <code>sql</code> is empty; <code>used_sql: false</code>.
          </li>
        </ul>
        <p>
          The client can display the clarifying questions to the user, collect answers, and re-submit
          a more specific query. The SDKs expose this via <code>metadata.reasoning</code>:
        </p>

        <h3>Python</h3>
        <CodeBlock
          language="python"
          code={`from seal import Seal

client = Seal("${SITE.defaultBaseUrl}", api_key="your-api-key")
result = client.query("show me the data")

if result.metadata.reasoning and result.metadata.reasoning.clarification_required:
    print("Need more info:", result.metadata.reasoning.clarifying_questions)
else:
    print(result.sql)
    print(result.results)`}
        />

        <h3>TypeScript</h3>
        <CodeBlock
          language="typescript"
          code={`import { Seal } from 'seal';

const client = new Seal({ baseUrl: '${SITE.defaultBaseUrl}', apiKey: 'your-api-key' });
const result = await client.query('show me the data');

if (result.metadata?.reasoning?.clarification_required) {
  console.log('Need more info:', result.metadata.reasoning.clarifying_questions);
} else {
  console.log(result.sql);
  console.log(result.results);
}`}
        />

        <h3>Example response (clarification required)</h3>
        <MetadataJsonBlock code={CHAT_METADATA_CLARIFICATION_JSON} />

        <h2>Metadata fields</h2>
        <p>
          All reasoning output appears under <code>metadata.reasoning</code> (JSON response) or at
          the top level of <code>seal.meta</code> SSE events. Fields:
        </p>
        <MetadataFieldList fields={REASONING_FIELDS} />

        <Callout variant="info" title="Fail-open design">
          If a reasoning layer throws an exception, the orchestrator logs a warning and records the
          layer in <code>layers_unavailable</code> with the skip reason. Other layers still run, and
          the response is never blocked by a reasoning failure.
        </Callout>

        <Callout variant="info" title="Latency budget">
          <code>REASONING_LATENCY_BUDGET_MS</code> (default 500) caps cumulative time for heuristic
          layers per phase. When exceeded, remaining layers are skipped with{' '}
          <code>layers_unavailable: {'{'}layer: &quot;latency_budget_exceeded&quot;{'}'}</code>.
          Set to <code>0</code> for unlimited.
        </Callout>

        <h2>SSE streaming</h2>
        <p>
          When chat streaming is enabled (<code>stream: true</code>), reasoning metadata appears on
          the <code>seal.meta</code> SSE event. A <strong>second</strong>{' '}
          <code>seal.meta</code> event may arrive after answer tokens complete with updated
          post-execution reasoning (e.g. follow-ups derived from the LLM answer). Clients should
          merge each <code>seal.meta</code> event for the same turn.
        </p>

        <h2>Trust gating</h2>
        <p>
          When <code>SEAL_TRUST_EXPLAINABILITY_ENABLED=false</code> (the production default),{' '}
          <code>research_notes</code> that reference schema details (table names, column names,
          schema size) are automatically stripped. This ensures end users do not see internal
          database structure through reasoning output. See{' '}
          <DocLink href="/docs/trust-explainability">Trust &amp; explainability</DocLink>.
        </p>

        <h2>Configuration</h2>
        <p>
          All <code>REASONING_*</code> env vars are workspace-hot-reloadable — changes apply
          immediately via the dashboard without restarting the API.
        </p>
        <ConfigReference rows={reasoningConfig} />

        <h2>Extending with custom layers</h2>
        <p>
          You can add custom reasoning layers by implementing the <code>ReasoningLayer</code>{' '}
          protocol:
        </p>
        <CodeBlock
          language="python"
          code={`from seal_core.reasoning.protocol import ReasoningLayer
from seal_core.reasoning.models import (
    ReasoningContext,
    ReasoningLayerResult,
    ReasoningPhase,
)


class MyCustomLayer:
    """Example custom reasoning layer."""

    name = "my_custom"
    phase = ReasoningPhase.POST_EXECUTION

    def enabled(self, ctx: ReasoningContext) -> bool:
        return ctx.exec_result is not None

    async def run(self, ctx: ReasoningContext) -> ReasoningLayerResult:
        notes = [f"Query returned {ctx.exec_result.row_count} rows"]
        return ReasoningLayerResult(
            layer_name=self.name,
            research_notes=notes,
        )`}
        />
        <p>
          Register the layer by extending <code>build_default_orchestrator()</code> or calling{' '}
          <code>orchestrator.register(MyLayer())</code> on the instance wired in{' '}
          <code>apps/api/app/main.py</code> (there is no <code>SEAL_REASONING_LAYERS</code> env var
          yet, unlike <code>SEAL_ENHANCERS</code>). If your layer introduces new metadata keys,
          follow the contract checklist in <code>docs/reasoning-layers.md</code> (OpenAPI,{' '}
          <code>stream_meta_metadata_keys.json</code>, shared TypeScript types).
        </p>

        <h2>Disabling heuristic reasoning</h2>
        <p>
          <code>REASONING_*</code> toggles control <strong>heuristic layers</strong> only. On chat,{' '}
          <code>ChatDecision</code> and the answer LLM (or stream enrichment) can still populate{' '}
          <code>metadata.reasoning</code> — those LLM calls are not gated by these flags.
        </p>
        <ul>
          <li>
            <code>REASONING_ENABLED=false</code> — skips heuristic pre/post layers on both routes
          </li>
          <li>
            <code>REASONING_CHAT_ENABLED=false</code> — skips heuristic layers on{' '}
            <code>/v1/chat</code> only (including <code>InferredContextLayer</code>)
          </li>
          <li>
            <code>REASONING_QUERY_ENABLED=false</code> — skips heuristic layers on{' '}
            <code>/v1/query</code> only
          </li>
          <li>
            <code>REASONING_CLARIFICATION_ENABLED=false</code> — skips heuristic clarification;
            chat <code>ChatDecision</code> may still set <code>clarification_required</code>
          </li>
          <li>
            <code>REASONING_ANALYSIS_FOLLOWUPS_ENABLED</code> /{' '}
            <code>REASONING_RESEARCH_NOTES_ENABLED</code> — query post layers only; chat uses the
            answer LLM for those fields
          </li>
        </ul>
        <p>
          The orchestrator is still invoked; disabled layers return empty partial metadata. To omit
          structured reasoning entirely you would need to change chat/query handlers — not supported
          via env today.
        </p>

        <h2>Related</h2>
        <p>
          <Link href="/docs/execution-metadata">Execution metadata</Link> ·{' '}
          <Link href="/docs/how-it-works">How Seal works</Link> ·{' '}
          <Link href="/docs/configuration#reasoning">Configuration → Reasoning</Link> ·{' '}
          <Link href="/docs/trust-explainability">Trust &amp; explainability</Link> ·{' '}
          <Link href="/docs/chat-streaming">SSE streaming</Link>
        </p>
      </DocsProse>
    </div>
  );
}
