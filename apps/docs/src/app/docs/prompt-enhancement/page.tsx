import { PageHeader } from '@/components/page-header';
import { Callout } from '@/components/docs/callout';
import { CodeBlock } from '@/components/code-block';
import { ConfigReference } from '@/components/docs/config-reference';
import { DocsProse } from '@/components/docs/docs-prose';
import { chatConfig } from '@/data/configuration-reference';
import Link from 'next/link';
import { SITE } from '@/lib/constants';

export default function PromptEnhancementPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Prompt enhancement"
        description="How chat turns gain schema, catalog, vector, and memory context before decision and answer LLMs run."
      />

      <DocsProse>
        <p>
          Natural-language chat would be shallow if every turn only saw the latest user sentence.
          Seal&apos;s <strong>enhancement chain</strong> (Vanna-style hooks) runs on{' '}
          <code>POST /v1/chat</code> when <code>CHAT_ENHANCEMENT_ENABLED=true</code> and the scope
          gate marked the turn <strong>in scope</strong>. It does not run on{' '}
          <code>POST /v1/query</code> — query uses the full schema via the planner directly.
        </p>
        <p>
          Enhancers mutate <strong>system prompts</strong> and optionally <strong>message lists</strong>{' '}
          before Instructor calls. They never execute SQL themselves; SQL still flows through the shared{' '}
          <code>execute_natural_language_query</code> pipeline after <code>ChatDecision.needs_data</code>{' '}
          is true.
        </p>

        <Callout variant="info" title="Default chain order">
          <strong>SchemaAware</strong> → <strong>VectorRag</strong> (if{' '}
          <code>VECTOR_STORE</code> ≠ <code>none</code>) → <strong>MultiTurn</strong>. Custom classes
          append via <code>SEAL_ENHANCERS</code>.
        </Callout>

        <h2>When hooks run</h2>
        <p>
          <code>EnhancementOrchestrator</code> is invoked from <code>ChatService</code> at specific{' '}
          <code>stage</code> values on <code>EnhancementContext</code>:
        </p>
        <ul>
          <li>
            <strong>decision</strong> — Before <code>ChatDecision</code> (does this question need SQL?)
          </li>
          <li>
            <strong>answer</strong> — Before the final answer LLM (or streamed completion)
          </li>
        </ul>
        <p>
          Each enhancer exposes <code>enhance_system_prompt</code> (once per stage invocation) and{' '}
          <code>enhance_user_messages</code> (can trim or augment the message list). Applied enhancer
          names accumulate in <code>metadata.enhancement.applied</code> on chat responses and in{' '}
          <code>seal.meta</code> SSE events.
        </p>

        <h2>Built-in enhancers</h2>
        <h3>SchemaAwareEnhancer</h3>
        <p>
          Selects up to <code>CHAT_MAX_CONTEXT_TABLES</code> relevant tables using the user question,
          schema introspection, and the global data catalog (including workspace description
          overrides). Appends focused DDL snippets, foreign-key hints, and catalog business language
          to the system prompt so the decision and answer models ground on real column names.
        </p>
        <p>
          <strong>Expect:</strong> Follow-ups like &quot;break that down by region&quot; reference tables
          mentioned earlier when those tables stay in the focused set.
        </p>

        <h3>VectorRagEnhancer</h3>
        <p>
          Embeds the user message (via LiteLLM embedding model), searches the configured vector store,
          and appends top-<code>RAG_TOP_K</code> text chunks. Disabled when{' '}
          <code>VECTOR_STORE=none</code>, when <code>in_scope=false</code>, or for very short messages.
        </p>
        <p>
          <strong>Expect:</strong> After <code>POST /v1/vector/reindex</code>, answers may cite document
          snippets from <code>RAG_DOCUMENTS_PATH</code> or catalog text in the index. No index → enhancer
          no-ops without failing the turn.
        </p>

        <h3>MultiTurnEnhancer</h3>
        <p>
          When session history exceeds <code>CHAT_SUMMARIZE_AFTER_MESSAGES</code>, older turns compress
          into a summary block. The answer stage still receives the last{' '}
          <code>CHAT_RECENT_MESSAGES</code> verbatim plus SQL preview rows (
          <code>CHAT_ANSWER_PREVIEW_ROWS</code>).
        </p>
        <p>
          <strong>Expect:</strong> Long sessions stay within token budgets; very old details may only
          appear in the summary, not verbatim.
        </p>

        <h2>Fail-open semantics</h2>
        <p>
          If an enhancer raises, the orchestrator logs a warning and continues with the previous prompt.
          Chat remains available even when Chroma is misconfigured or an optional dependency is missing.
        </p>

        <h2>Disable enhancement</h2>
        <p>Per request (agent already has RAG/schema):</p>
        <CodeBlock
          language="bash"
          code={`curl -s -X POST "${SITE.defaultBaseUrl}/v1/chat" \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: your-api-key" \\
  -d '{"message":"Hello","enhancement":false}'`}
        />
        <CodeBlock language="python" code={`client.chat("Hello", enhancement=False)`} />
        <CodeBlock
          language="typescript"
          code={`await client.chat('Hello', { enhancement: false });`}
        />
        <p>
          Globally: set <code>CHAT_ENHANCEMENT_ENABLED=false</code> or toggle via workspace settings.
        </p>

        <h2>Environment</h2>
        <ConfigReference rows={chatConfig} />

        <h2>Custom enhancers</h2>
        <p>
          Implement <code>PromptEnhancer</code> in Python and register{' '}
          <code>SEAL_ENHANCERS=my_package.MyEnhancer</code>. See contributor doc{' '}
          <code>docs/integrations/custom-enhancers.md</code> and{' '}
          <Link href="/docs/vector-rag">Vector RAG</Link> for store setup.
        </p>

        <p>
          Related: <Link href="/docs/guardrails">Guardrails</Link> ·{' '}
          <Link href="/docs/how-it-works">How Seal works</Link> ·{' '}
          <Link href="/docs/data-catalog">Data catalog</Link>.
        </p>
      </DocsProse>
    </div>
  );
}
