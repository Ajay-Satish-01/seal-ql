import Link from 'next/link';
import { Callout } from '@/components/docs/callout';
import { DocLink } from '@/components/docs/doc-link';
import { CodeBlock } from '@/components/code-block';
import { PageHeader } from '@/components/page-header';
import { SITE } from '@/lib/constants';
import {
  curlChat,
  curlDeleteSession,
  curlListSessions,
  localDevSetupSnippet,
  pythonChatSnippet,
  tsChatSnippet,
} from '@/lib/doc-snippets';

export default function ChatQaPage() {
  const base = SITE.defaultBaseUrl;

  return (
    <div className="w-full">
      <PageHeader
        title="Chat & Q&A"
        description="Schema-grounded conversational analytics with optional charts, streaming, and session memory."
      />

      <Callout variant="info" title="Global data catalog">
        The auto-generated catalog at <code>config/catalog.yaml</code> is used by{' '}
        <code>POST /v1/chat</code>, <code>POST /v1/query</code>, and the query planner. Edit{' '}
        <code>table_description</code> or <code>view_description</code> to improve answers — see{' '}
        <Link href="/docs/data-catalog" className="text-primary underline-offset-4 hover:underline">
          Data catalog
        </Link>
        .
      </Callout>

      <h2 className="font-heading mt-8 text-xl font-semibold">Local setup</h2>
      <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
        From a repo clone (contributors) or use the{' '}
        <Link href="/docs/self-hosting" className="text-primary underline-offset-4 hover:underline">
          Docker image
        </Link>{' '}
        for production.
      </p>
      <CodeBlock language="bash" code={localDevSetupSnippet()} />

      <h2 className="font-heading mt-8 text-xl font-semibold">Request body</h2>
      <ul className="text-muted-foreground mt-4 list-disc space-y-2 pl-6 text-sm">
        <li>
          <code>message</code> (required) — latest user turn
        </li>
        <li>
          <code>session_id</code> — return value from prior response for follow-ups
        </li>
        <li>
          <code>database_id</code> — registered backend (default <code>&quot;default&quot;</code>).
          Send on <strong>every</strong> turn when using <code>session_id</code>. See{' '}
          <Link href="/docs/multi-database" className="text-primary underline-offset-4 hover:underline">
            Multi-database routing
          </Link>{' '}
          for pinning rules (successful turns pin the id; refusals do not).
        </li>
        <li>
          <code>include_charts</code> — attach Vega-Lite chart when SQL runs (default false)
        </li>
        <li>
          <code>stream</code> — SSE for the final answer only (
          <Link href="/docs/chat-streaming" className="text-primary underline-offset-4 hover:underline">
            streaming guide
          </Link>
          )
        </li>
        <li>
          <code>enhancement</code> — override <code>CHAT_ENHANCEMENT_ENABLED</code> for this request
        </li>
      </ul>

      <h2 className="font-heading mt-8 text-xl font-semibold">Examples</h2>
      <h3 className="text-foreground mt-6 text-lg font-medium">curl</h3>
      <CodeBlock
        language="bash"
        code={`# First message
${curlChat(base, 'What tables are in the database?')}

# Follow-up (use session_id from JSON response)
${curlChat(base, 'Show revenue for the largest table', { sessionId: 'YOUR_SESSION_ID', includeCharts: true })}`}
      />

      <h3 className="text-foreground mt-6 text-lg font-medium">Python SDK</h3>
      <CodeBlock language="python" code={pythonChatSnippet(base, 'Orders by region last week', { includeCharts: true })} />

      <h3 className="text-foreground mt-6 text-lg font-medium">TypeScript SDK</h3>
      <CodeBlock
        language="typescript"
        code={tsChatSnippet(base, 'Orders by region last week', { includeCharts: true })}
      />

      <h2 className="font-heading mt-8 text-xl font-semibold">Session history &amp; explainability</h2>
      <p className="text-muted-foreground mt-4 text-sm leading-relaxed">
        With <code>CHAT_SESSION_STORE=postgres</code> (and <code>scripts/migrate_app.sql</code>{' '}
        applied), conversations persist in <code>seal_app.chat_sessions</code>. Each assistant
        message stores an <strong>explainability snapshot</strong> — the SQL, sources, metadata,
        chart spec, and result preview from that turn. When you load a past session, the same
        explainability data is available for review. The operational dashboard (
        <code>apps/web</code>, port 3001) lists past chats and resumes them with per-turn
        explainability buttons. API endpoints:
      </p>
      <ul className="text-muted-foreground mt-4 list-disc space-y-2 pl-6 text-sm">
        <li>
          <code>GET /v1/chat/sessions</code> — list sessions (optional{' '}
          <code>database_id</code> filter)
        </li>
        <li>
          <code>GET /v1/chat/sessions/&#123;session_id&#125;</code> — full message history
        </li>
        <li>
          <code>DELETE /v1/chat/sessions/&#123;session_id&#125;</code> — remove a session
        </li>
      </ul>
      <h3 className="text-foreground mt-6 text-lg font-medium">curl</h3>
      <CodeBlock
        language="bash"
        code={`${curlListSessions(base)}

${curlDeleteSession(base, 'YOUR_SESSION_ID')}`}
      />

      <h2 className="font-heading mt-8 text-xl font-semibold">Response fields</h2>
      <ul className="text-muted-foreground mt-4 list-disc space-y-2 pl-6 text-sm">
        <li>
          <code>session_id</code>, <code>message</code> — always present
        </li>
        <li>
          <code>sql</code>, <code>results</code>, <code>chart</code> — when the turn runs SQL
        </li>
        <li>
          <code>columns</code> — typed result columns when SQL runs (same as query)
        </li>
        <li>
          <code>sources</code>, <code>metadata</code> — tables used, execution stats (
          <code>row_count</code>, <code>execution_time_ms</code>, <code>repair_attempts</code>,{' '}
          <code>used_sql</code>), <code>metadata.enhancement</code> (
          <code>enabled</code>, <code>applied</code>, optional skip/unavailable reasons), and{' '}
          <code>metadata.scope</code> (refusals set <code>refusal: true</code>,{' '}
          <code>metadata.suggested_queries</code> with example in-scope questions,{' '}
          <code>used_sql: false</code>, no <code>sql</code>)
        </li>
      </ul>

      <p className="text-muted-foreground mt-4 text-sm leading-relaxed">
        Full field reference: <DocLink href="/docs/execution-metadata">Execution metadata</DocLink>.
        Provenance and scope details:{' '}
        <DocLink href="/docs/trust-explainability">Trust &amp; explainability</DocLink>.
      </p>

      <Callout variant="warning" title="Multi-database sessions">
        If you use <code>database_id=&quot;analytics&quot;</code> on the first message, repeat{' '}
        <code>database_id=&quot;analytics&quot;</code> on all follow-ups with the same{' '}
        <code>session_id</code>. Switching ids mid-session returns HTTP 400{' '}
        <code>session_database_id_mismatch</code> after the session is pinned.
      </Callout>

      <h2 className="font-heading mt-8 text-xl font-semibold">Batteries included</h2>
      <p className="text-muted-foreground mt-4 text-sm leading-relaxed">
        <code>make up</code> enables prompt enhancement and catalog sync by default (
        <code>CHAT_ENHANCEMENT_ENABLED=true</code>, <code>VECTOR_STORE=none</code>). Optional Chroma
        RAG: <Link href="/docs/vector-rag" className="text-primary underline-offset-4 hover:underline">Vector RAG</Link>
        . For Mastra/LangChain, use{' '}
        <Link href="/docs/agent-frameworks" className="text-primary underline-offset-4 hover:underline">
          Agent frameworks
        </Link>
        . Try live chat on the <Link href="/demo" className="text-primary underline-offset-4 hover:underline">demo</Link>.
      </p>
    </div>
  );
}
