import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';

export default function TypeScriptSDKPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="TypeScript SDK"
        description="Integrate Intelligence Connector into your JS/TS frontends and Node.js services."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none text-lg leading-relaxed">
        <h2 className="text-foreground mt-10 mb-4 text-2xl font-bold">Installation</h2>
        <p>
          The TypeScript SDK relies on <code>pnpm</code>.
        </p>
        <CodeBlock code={`cd sdks/typescript\npnpm install`} />

        <h2 className="text-foreground mt-10 mb-4 text-2xl font-bold">Basic Usage</h2>
        <CodeBlock
          language="typescript"
          code={`import { IntelligenceClient } from '@intelligence-connector/sdk';

const client = new IntelligenceClient({
  apiUrl: 'http://localhost:8000'
});

async function run() {
  const result = await client.query("Monthly revenue trends by region");

  console.log(result.sql);        // Validated, safe, optimized SQL
  console.log(result.data);       // Executed database results
  console.log(result.chartSpec);  // Custom Vega-Lite visualization spec
}

run();`}
        />
      </div>
    </div>
  );
}
