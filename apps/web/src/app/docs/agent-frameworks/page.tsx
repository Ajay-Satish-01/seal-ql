import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import Link from 'next/link';
import { SITE } from '@/lib/constants';
import { curlChat, curlWithAuth, tsChatSnippet, tsQuerySnippet } from '@/lib/doc-snippets';

export default function AgentFrameworksPage() {
  const base = SITE.defaultBaseUrl;

  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Agent frameworks"
        description="Register Seal as HTTP tools for Mastra, LangChain, or custom agents — optional when using built-in chat."
      />

      <h2 className="font-heading mt-6 text-xl font-semibold">Tools</h2>
      <table className="text-muted-foreground mt-4 w-full text-sm">
        <thead>
          <tr className="border-border border-b text-left">
            <th className="py-2 pr-4">Tool</th>
            <th className="py-2">Endpoint</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-border/40 border-b">
            <td className="py-2 pr-4 font-mono">seal_get_schema</td>
            <td className="py-2">GET /v1/schema</td>
          </tr>
          <tr className="border-border/40 border-b">
            <td className="py-2 pr-4 font-mono">seal_get_catalog</td>
            <td className="py-2">GET /v1/catalog</td>
          </tr>
          <tr className="border-border/40 border-b">
            <td className="py-2 pr-4 font-mono">seal_query</td>
            <td className="py-2">POST /v1/query</td>
          </tr>
          <tr>
            <td className="py-2 pr-4 font-mono">seal_chat</td>
            <td className="py-2">POST /v1/chat</td>
          </tr>
        </tbody>
      </table>

      <h2 className="font-heading mt-8 text-xl font-semibold">Tool manifest</h2>
      <p className="text-muted-foreground mt-2 text-sm">
        OpenAI function-calling format (download and register in your agent host):
      </p>
      <p className="text-muted-foreground mt-2 text-sm">
        Download{' '}
        <a href="/seal-tools.openai.json" className="text-primary underline-offset-4 hover:underline">
          seal-tools.openai.json
        </a>{' '}
        from this site, or copy <code>config/seal-tools.openai.json</code> from the repository (
        synced via <code>make sync-docs-assets</code>).
      </p>

      <h2 className="font-heading mt-8 text-xl font-semibold">HTTP examples</h2>
      <CodeBlock language="bash" code={curlWithAuth(base, 'GET', '/v1/schema')} />
      <CodeBlock language="bash" code={curlWithAuth(base, 'GET', '/v1/catalog')} />
      <CodeBlock
        language="bash"
        code={curlWithAuth(base, 'POST', '/v1/query', {
          query: 'Revenue by month',
          database_id: 'default',
        })}
      />
      <CodeBlock language="bash" code={curlChat(base, 'Explain revenue last quarter', { includeCharts: true })} />

      <h2 className="font-heading mt-8 text-xl font-semibold">TypeScript SDK (in-process)</h2>
      <CodeBlock language="typescript" code={tsQuerySnippet(base, 'Revenue by month')} />
      <CodeBlock
        language="typescript"
        code={tsChatSnippet(base, 'Explain revenue last quarter', { includeCharts: true })}
      />

      <h2 className="font-heading mt-8 text-xl font-semibold">Composition patterns</h2>
      <ul className="text-muted-foreground mt-4 list-disc space-y-2 pl-6 text-sm">
        <li>
          <strong>Seal-only:</strong> Your app calls <code>client.chat()</code> — enhancement + catalog on by default.
        </li>
        <li>
          <strong>Framework orchestration:</strong> Register HTTP tools; set <code>VECTOR_STORE=none</code> and{' '}
          <code>enhancement: false</code> to avoid duplicate RAG.
        </li>
        <li>
          <strong>Hybrid:</strong> Framework for planning; <code>seal_query</code> for safe SQL + charts.
        </li>
      </ul>

      <p className="text-muted-foreground mt-6 text-sm">
        Built-in chat needs no framework —{' '}
        <Link href="/docs/chat-qa" className="text-primary underline-offset-4 hover:underline">
          Chat &amp; Q&amp;A
        </Link>
        .
      </p>
    </div>
  );
}
