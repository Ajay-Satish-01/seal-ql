import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { Callout } from '@/components/docs/callout';
import { PACKAGES_IN_PROGRESS_NOTE, SITE } from '@/lib/constants';
import {
  pythonCatalogSnippet,
  pythonChatSnippet,
  pythonChatStreamSnippet,
  pythonQuerySnippet,
  pythonSdkInstallSnippet,
} from '@/lib/doc-snippets';

export default function PythonSDKPage() {
  return (
    <div className="w-full">
      <PageHeader
        title="Python SDK"
        description="Integrate Seal from Python applications."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <h2 className="text-foreground mt-4 text-2xl font-bold">Installation</h2>
        {!SITE.packagesPublished ? (
          <Callout variant="info" title="PyPI publish in progress">
            {PACKAGES_IN_PROGRESS_NOTE}
          </Callout>
        ) : null}
        <CodeBlock language="bash" code={pythonSdkInstallSnippet()} />
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
          Pass <code>api_key=</code> on every request (sent as <code>X-API-Key</code>). See{' '}
          <Link href="/docs/authentication">Authentication</Link>.
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
          code={pythonQuerySnippet(SITE.defaultBaseUrl, 'Show total revenue by product category')}
        />
        <p>
          Named backends use the keyword <code>database_id=</code> on every method that touches a
          database:
        </p>
        <CodeBlock
          language="python"
          code={`result = client.query("Total orders", database_id="default")
schema = client.schema(database_id="analytics")
reply = client.chat("What tables exist?", database_id="analytics")
for event in client.chat_stream("Summarize", database_id="analytics"):
    if event["type"] == "meta":
        print(event["data"].get("database_id"), event["data"].get("sql"))`}
        />
        <p>
          See <Link href="/docs/multi-database">Multi-database routing</Link> for YAML/JSON config,
          DuckDB paths, and chat session pinning.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Chat &amp; catalog</h2>
        <CodeBlock
          language="python"
          code={pythonCatalogSnippet(SITE.defaultBaseUrl)}
        />
        <CodeBlock
          language="python"
          code={pythonChatSnippet(SITE.defaultBaseUrl, 'Revenue by region?', {
            sessionId: 'user-1',
            includeCharts: true,
          })}
        />
        <CodeBlock
          language="python"
          code={pythonChatStreamSnippet(SITE.defaultBaseUrl, 'Summarize that')}
        />

        <h2 className="text-foreground mt-10 text-2xl font-bold">Async client</h2>
        <CodeBlock
          language="python"
          code={`from seal import AsyncSeal

async with AsyncSeal("${SITE.defaultBaseUrl}", api_key="your-secret") as client:
    result = await client.query("Hourly event counts")
    chat = await client.chat("Follow-up question?")
    async for event in client.chat_stream("Stream this answer"):
        if event["type"] == "delta":
            print(event["content"], end="")`}
        />

        <h2 className="text-foreground mt-10 text-2xl font-bold">Errors</h2>
        <p>
          <code>QueryError</code> (4xx), <code>ServerError</code> (5xx),{' '}
          <code>ConnectionError</code> for network issues.
        </p>

        <p>
          <Link href="/demo">Demo</Link> ·{' '}
          <Link href="/docs/chat-qa">Chat &amp; Q&amp;A</Link> ·{' '}
          <Link href="/docs/integration-guide">Integration Guide</Link>
        </p>
      </div>
    </div>
  );
}
