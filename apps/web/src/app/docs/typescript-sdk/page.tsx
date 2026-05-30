import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { Callout } from '@/components/docs/callout';
import { SITE } from '@/lib/constants';

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
          code={`npm install intelligence-sdk
npm install react react-dom vega vega-lite vega-embed`}
        />

        <Callout variant="info" title="Connect to your API">
          Run the <Link href="/docs/self-hosting">Docker image</Link>, then set <code>baseUrl</code>{' '}
          to your deployment URL.
        </Callout>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Client</h2>
        <CodeBlock
          language="typescript"
          code={`import { IntelligenceConnector } from 'intelligence-sdk';

const client = new IntelligenceConnector({
  baseUrl: '${SITE.defaultBaseUrl}',
});

const result = await client.query('Orders by region');
console.log(result.sql, result.results, result.chart);`}
        />

        <h2 className="text-foreground mt-10 text-2xl font-bold">VegaChart (React)</h2>
        <p>
          Pass the full <code>ChartSpec</code> from the API — not raw Vega-Lite JSON alone.
        </p>
        <CodeBlock
          language="tsx"
          code={`'use client';

import { IntelligenceConnector, VegaChart } from 'intelligence-sdk';

export async function ChartExample() {
  const client = new IntelligenceConnector({ baseUrl: '${SITE.defaultBaseUrl}' });
  const result = await client.query('Revenue by category');

  if (!result.chart || result.chart.chart_type === 'table') {
    return <pre>{JSON.stringify(result.results, null, 2)}</pre>;
  }

  return <VegaChart spec={result.chart} theme="dark" actions />;
}`}
        />

        <h2 className="text-foreground mt-10 text-2xl font-bold">Errors</h2>
        <p>
          <code>QueryError</code>, <code>ServerError</code>, <code>ConnectionError</code> from{' '}
          <code>intelligence-sdk</code>.
        </p>

        <p>
          <Link href="/demo">Demo</Link> ·{' '}
          <Link href="/docs/charts-analysis">Charts &amp; Analysis</Link>
        </p>
      </div>
    </div>
  );
}
