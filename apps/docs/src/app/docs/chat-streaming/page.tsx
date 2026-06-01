import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { Callout } from '@/components/docs/callout';
import { SITE } from '@/lib/constants';
import {
  curlChat,
  pythonChatStreamSnippet,
  tsChatStreamSnippet,
} from '@/lib/doc-snippets';

export default function ChatStreamingPage() {
  const base = SITE.defaultBaseUrl;

  return (
    <div className="max-w-3xl">
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
        <Link href="/docs/multi-database" className="text-primary underline-offset-4 hover:underline">
          Multi-database routing
        </Link>
        .
      </p>
      <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
        Invalid <code>database_id</code> or session mismatch errors return HTTP 400 before any SSE
        events are sent.
      </p>

      <h2 className="font-heading mt-8 text-xl font-semibold">SSE event order</h2>
      <ol className="text-muted-foreground mt-4 list-decimal space-y-2 pl-6 text-sm">
        <li>
          <code>event: seal.meta</code> — <code>session_id</code>, <code>database_id</code>,{' '}
          <code>sources</code>, <code>sql</code>, <code>chart</code>, <code>enhancement</code>,{' '}
          <code>scope</code>
        </li>
        <li>
          <code>data: {'{...}'}</code> — OpenAI-style <code>chat.completion.chunk</code> deltas
        </li>
        <li>
          <code>data: [DONE]</code> — end of stream
        </li>
      </ol>

      <p className="text-muted-foreground mt-6 text-sm">
        Non-streaming JSON: set <code>stream: false</code> (default). See{' '}
        <Link href="/docs/chat-qa" className="text-primary underline-offset-4 hover:underline">
          Chat &amp; Q&amp;A
        </Link>{' '}
        and the <Link href="/demo" className="text-primary underline-offset-4 hover:underline">demo</Link>{' '}
        streaming panel.
      </p>
    </div>
  );
}
