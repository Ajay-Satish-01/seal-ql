import { PageHeader } from '@/components/page-header';
import { Callout } from '@/components/docs/callout';
import { DocLink } from '@/components/docs/doc-link';
import { MetadataJsonBlock } from '@/components/docs/metadata-json-block';
import { SITE } from '@/lib/constants';
import {
  curlChat,
  pythonChatStreamSnippet,
  tsChatStreamSnippet,
} from '@/lib/doc-snippets';
import { CHAT_STREAM_META_JSON } from '@/lib/execution-metadata';
import { CodeBlock } from '@/components/code-block';

export default function ChatStreamingPage() {
  const base = SITE.defaultBaseUrl;

  return (
    <div className="w-full">
      <PageHeader
        title="Chat streaming"
        description="Stream only the final natural-language answer; SQL and charts arrive in seal.meta first."
      />

      <Callout variant="warning" title="What is not streamed">
        The decision step, SQL generation, execution, and chart building complete before SSE starts.
        The stream carries the final assistant prose only.
      </Callout>

      <h2 className="font-heading mt-6 text-xl font-semibold">curl</h2>
      <CodeBlock language="bash" code={curlChat(base, 'Summarize revenue trends', { stream: true, includeCharts: true })} />

      <h2 className="font-heading mt-8 text-xl font-semibold">Python SDK</h2>
      <CodeBlock language="python" code={pythonChatStreamSnippet(base, 'Summarize revenue trends')} />

      <h2 className="font-heading mt-8 text-xl font-semibold">TypeScript SDK</h2>
      <CodeBlock language="typescript" code={tsChatStreamSnippet(base, 'Summarize revenue trends')} />

      <h2 className="font-heading mt-8 text-xl font-semibold">database_id and seal.meta</h2>
      <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
        Pass <code>database_id</code> in the JSON body the same as non-streaming chat. The first
        event includes <code>database_id</code> so clients can confirm which backend ran before
        reading streamed text. Use the same <code>database_id</code> on every message in a{' '}
        <code>session_id</code> — see{' '}
        <DocLink href="/docs/multi-database">Multi-database routing</DocLink>
        .
      </p>
      <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
        Invalid <code>database_id</code> or session mismatch errors return HTTP 400 before any SSE
        events are sent.
      </p>

      <h2 className="font-heading mt-8 text-xl font-semibold">SSE event order</h2>
      <ol className="text-muted-foreground mt-4 list-decimal space-y-2 pl-6 text-sm">
        <li>
          <code>event: seal.meta</code> — flat JSON (not nested under <code>metadata</code>):{' '}
          <code>session_id</code>, <code>sources</code>, <code>sql</code>, <code>results</code>,{' '}
          <code>columns</code>, <code>chart</code>, execution fields (
          <code>database_id</code>, <code>row_count</code>, <code>execution_time_ms</code>,{' '}
          <code>truncated</code>, <code>warnings</code>, <code>repair_attempts</code>,{' '}
          <code>used_sql</code>), <code>enhancement</code>, <code>scope</code>, and{' '}
          <code>refusal</code> / <code>sql_error</code> when applicable. See{' '}
          <DocLink href="/docs/execution-metadata">Execution metadata</DocLink>
          .
        </li>
        <li>
          <code>data: {'{...}'}</code> — OpenAI-style <code>chat.completion.chunk</code> deltas
        </li>
        <li>
          Optional <code>event: seal.error</code> — client-visible failure (e.g. LLM rate limit) with{' '}
          <code>{'{"code":"rate_limit","message":"..."}'}</code> before <code>[DONE]</code> when the
          stream cannot complete. Mapped to <code>stream_error</code> in SDKs and the dashboard.
        </li>
        <li>
          <code>data: [DONE]</code> — end of stream
        </li>
      </ol>

      <h3 className="text-foreground mt-6 text-lg font-medium">Example seal.meta payload</h3>
      <MetadataJsonBlock title="Example seal.meta payload" code={CHAT_STREAM_META_JSON} className="mt-6" />

      <Callout variant="info" title="Client validation (SDK / dashboard / demo)">
        The TypeScript SDK maps SSE frames with <code>mapChatSseEvent</code>. Malformed{' '}
        <code>seal.meta</code> (for example invalid <code>scope.source</code>) yields a{' '}
        <code>meta_error</code> event with <code>partial</code> fields when{' '}
        <code>session_id</code> / <code>database_id</code> are still readable; answer deltas may
        continue. LLM provider throttling surfaces as <code>seal.error</code> (
        <code>stream_error</code>) — not HTTP 429 on the chat stream; non-streaming routes return{' '}
        <strong>503</strong> with a rate-limit message. Same rules in <code>shared/stream-meta.ts</code>{' '}
        used by the dashboard and docs demo.
      </Callout>

      <p className="text-muted-foreground mt-6 text-sm">
        Non-streaming JSON: set <code>stream: false</code> (default). See{' '}
        <DocLink href="/docs/chat-qa">Chat &amp; Q&amp;A</DocLink> and the{' '}
        <DocLink href="/demo">demo</DocLink> streaming panel.
      </p>
    </div>
  );
}
