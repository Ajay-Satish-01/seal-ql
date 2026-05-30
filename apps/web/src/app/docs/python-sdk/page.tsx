import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { Callout } from '@/components/docs/callout';
import { SITE } from '@/lib/constants';

export default function PythonSDKPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Python SDK"
        description="Integrate Intelligence Connector from Python applications."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <h2 className="text-foreground mt-4 text-2xl font-bold">Installation</h2>
        <CodeBlock language="bash" code="pip install intelligence-connector" />
        <p>
          Monorepo contributors: <code>uv sync --all-packages --all-extras</code> from the repo
          root.
        </p>

        <Callout variant="info" title="Connect to your API">
          Install the SDK in your app, run the <Link href="/docs/self-hosting">Docker image</Link>,
          then point the client at your <code>baseUrl</code>.
        </Callout>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Basic usage</h2>
        <CodeBlock
          language="python"
          code={`from intelligence_connector import IntelligenceConnector

with IntelligenceConnector("${SITE.defaultBaseUrl}") as client:
    schema = client.schema()
    result = client.query("Show total revenue by product category")

print(result.sql)
print(result.results)
if result.chart:
    print(result.chart.chart_type)
    print(result.chart.vega_lite_spec)`}
        />

        <h2 className="text-foreground mt-10 text-2xl font-bold">Async client</h2>
        <CodeBlock
          language="python"
          code={`from intelligence_connector import AsyncIntelligenceConnector

async with AsyncIntelligenceConnector("${SITE.defaultBaseUrl}") as client:
    result = await client.query("Hourly event counts")`}
        />

        <h2 className="text-foreground mt-10 text-2xl font-bold">Errors</h2>
        <p>
          <code>QueryError</code> (4xx), <code>ServerError</code> (5xx),{' '}
          <code>ConnectionError</code> for network issues.
        </p>

        <p>
          <Link href="/demo">Demo</Link> ·{' '}
          <Link href="/docs/integration-guide">Integration Guide</Link>
        </p>
      </div>
    </div>
  );
}
