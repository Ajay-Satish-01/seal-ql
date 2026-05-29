import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';

export default function PythonSDKPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Python SDK"
        description="Integrate Intelligence Connector into your Python applications."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none text-lg leading-relaxed">
        <h2 className="text-foreground mt-10 mb-4 text-2xl font-bold">Installation</h2>
        <p>
          We use <code>uv</code> to manage workspaces and dependencies.
        </p>
        <CodeBlock code="uv sync --all-packages --all-extras" />

        <h2 className="text-foreground mt-10 mb-4 text-2xl font-bold">Basic Usage</h2>
        <p>
          The SDK allows you to query your database using natural language, returning validated SQL,
          the raw data, and a visualization schema.
        </p>
        <CodeBlock
          language="python"
          code={`from intelligence_connector import IntelligenceClient

client = IntelligenceClient(api_url="http://localhost:8000")

response = client.query("Show me monthly revenue trends by region")

print(response.sql)         # Safe, AST-validated SQL
print(response.data)        # Executed results
print(response.chart_spec)  # Vega-Lite JSON Spec`}
        />

        <h2 className="text-foreground mt-10 mb-4 text-2xl font-bold">Testing</h2>
        <p>Run tests across all Python workspaces safely:</p>
        <CodeBlock code="uv run pytest -v" />
      </div>
    </div>
  );
}
