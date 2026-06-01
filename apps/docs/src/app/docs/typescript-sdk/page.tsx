import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { Callout } from '@/components/docs/callout';
import { SITE } from '@/lib/constants';
import {
  tsCatalogSnippet,
  tsChatSnippet,
  tsChatStreamSnippet,
  tsQuerySnippet,
} from '@/lib/doc-snippets';

export default function TypeScriptSDKPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="TypeScript SDK"
        description="Query your database and render Vega-Lite charts in React."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <h2 className="text-foreground mt-4 text-2xl font-bold">Installation</h2>
        <CodeBlock
          language="bash"
          code={`npm install seal
npm install react react-dom vega vega-lite vega-embed`}
        />

        <Callout variant="info" title="Connect to your API">
          Run the <Link href="/docs/self-hosting">Docker image</Link>, then set <code>baseUrl</code>{' '}
          to your deployment URL.
        </Callout>

        <h2 className="text-foreground mt-10 text-2xl font-bold">API key</h2>
        <p>
          When the server has <code>SEAL_API_KEY</code> set, pass <code>apiKey</code> (sent as{' '}
          <code>X-API-Key</code>). If you also pass custom <code>headers</code>,{' '}
          <code>apiKey</code> wins over any <code>X-API-Key</code> in that object. See{' '}
          <Link href="/docs/authentication">Authentication</Link>.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Client</h2>
        <CodeBlock
          language="typescript"
          code={tsQuerySnippet(SITE.defaultBaseUrl, 'Orders by region')}
        />
        <p>
          Multiple databases: pass the id as the <strong>second argument</strong> to{' '}
          <code>query</code>, and use <code>databaseId</code> in the options object for chat and
          schema:
        </p>
        <CodeBlock
          language="typescript"
          code={`const orders = await client.query('Total orders today', 'default');
const revenue = await client.query('Daily revenue trend', 'analytics');
const schema = await client.schema({ databaseId: 'analytics' });
const reply = await client.chat('Summarize revenue', { databaseId: 'analytics' });
for await (const event of client.chatStream('Trend by week', { databaseId: 'analytics' })) {
  if (event.type === 'meta') console.log(event.data.database_id, event.data.sql);
}`}
        />
        <p>
          See <Link href="/docs/multi-database">Multi-database routing</Link> for configuration and
          chat session pinning.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">VegaChart (React)</h2>
        <p>
          Pass the full <code>ChartSpec</code> from the API — not raw Vega-Lite JSON alone.
        </p>
        <CodeBlock
          language="tsx"
          code={`'use client';

import { Seal, VegaChart } from 'seal';

export async function ChartExample() {
  const client = new Seal({
    baseUrl: '${SITE.defaultBaseUrl}',
    apiKey: process.env.SEAL_API_KEY,
  });
  const result = await client.query('Revenue by category');

  if (!result.chart || result.chart.chart_type === 'table') {
    return <pre>{JSON.stringify(result.results, null, 2)}</pre>;
  }

  return <VegaChart spec={result.chart} theme="dark" actions />;
}`}
        />

        <h2 className="text-foreground mt-10 text-2xl font-bold">Chat &amp; catalog</h2>
        <CodeBlock language="typescript" code={tsCatalogSnippet(SITE.defaultBaseUrl)} />
        <CodeBlock
          language="typescript"
          code={tsChatSnippet(SITE.defaultBaseUrl, 'Orders last week?', {
            includeCharts: true,
            sessionId: 'user-1',
          })}
        />
        <CodeBlock
          language="typescript"
          code={tsChatStreamSnippet(SITE.defaultBaseUrl, 'Summarize revenue')}
        />

        <h2 className="text-foreground mt-10 text-2xl font-bold">Errors</h2>
        <p>
          <code>QueryError</code>, <code>ServerError</code>, <code>ConnectionError</code> from{' '}
          <code>seal</code>.
        </p>

        <p>
          <Link href="/demo">Demo</Link> ·{' '}
          <Link href="/docs/chat-qa">Chat &amp; Q&amp;A</Link> ·{' '}
          <Link href="/docs/charts-analysis">Charts &amp; Analysis</Link>
        </p>
      </div>
    </div>
  );
}
