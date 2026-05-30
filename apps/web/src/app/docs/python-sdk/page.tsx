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
        description="Integrate Seal from Python applications."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <h2 className="text-foreground mt-4 text-2xl font-bold">Installation</h2>
        <CodeBlock language="bash" code="pip install seal" />
        <p>
          Monorepo contributors: <code>uv sync --all-packages --all-extras</code> from the repo
          root.
        </p>

        <Callout variant="info" title="Connect to your API">
          Install the SDK in your app, run the <Link href="/docs/self-hosting">Docker image</Link>,
          then point the client at your <code>baseUrl</code>.
        </Callout>

        <h2 className="text-foreground mt-10 text-2xl font-bold">API key</h2>
        <p>
          When the server has <code>SEAL_API_KEY</code> set, pass <code>api_key=</code> (sent as{' '}
          <code>X-API-Key</code>). See <Link href="/docs/authentication">Authentication</Link>.
        </p>
        <CodeBlock
          language="python"
          code={`import os
from seal import Seal

with Seal(
    "${SITE.defaultBaseUrl}",
    api_key=os.environ["SEAL_API_KEY"],
) as client:
    client.schema()`}
        />

        <h2 className="text-foreground mt-10 text-2xl font-bold">Basic usage</h2>
        <CodeBlock
          language="python"
          code={`from seal import Seal

with Seal("${SITE.defaultBaseUrl}", api_key="your-secret") as client:
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
          code={`from seal import AsyncSeal

async with AsyncSeal("${SITE.defaultBaseUrl}") as client:
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
