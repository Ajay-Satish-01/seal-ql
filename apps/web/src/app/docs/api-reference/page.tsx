import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';

export default function ApiReferencePage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="API Reference"
        description="Detailed breakdown of the REST API endpoints."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <h2>POST /query</h2>
        <p>
          The primary endpoint for natural language querying. It translates the prompt, executes the
          SQL safely, and returns the data alongside a generated visualization schema.
        </p>

        <h3>Request Body</h3>
        <p>
          Content-Type: <code>application/json</code>
        </p>
        <CodeBlock
          language="json"
          code={`{
  "query": "Show me the top 5 customers by revenue this month",
  "llm_config": {
    "provider": "ollama",
    "model": "llama3.2:1b"
  }
}`}
        />

        <div className="my-6">
          <table className="border-border/50 w-full border-collapse border text-left text-sm">
            <thead className="bg-muted text-foreground">
              <tr>
                <th className="border-border/50 border p-2">Field</th>
                <th className="border-border/50 border p-2">Type</th>
                <th className="border-border/50 border p-2">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border-border/50 border p-2 font-mono">query</td>
                <td className="border-border/50 border p-2">string</td>
                <td className="border-border/50 border p-2">The natural language question.</td>
              </tr>
              <tr>
                <td className="border-border/50 border p-2 font-mono">llm_config (optional)</td>
                <td className="border-border/50 border p-2">object</td>
                <td className="border-border/50 border p-2">
                  Override the default LLM provider and model for this specific query.
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <h3>Response</h3>
        <p>Returns a 200 OK with the generated SQL, result set, and Vega-Lite chart schema.</p>
        <CodeBlock
          language="json"
          code={`{
  "sql": "SELECT name, SUM(amount) as revenue FROM users JOIN payments ON users.id = payments.user_id GROUP BY name ORDER BY revenue DESC LIMIT 5",
  "columns": ["name", "revenue"],
  "results": [
    {"name": "Acme Corp", "revenue": 15000},
    {"name": "Globex", "revenue": 12500}
  ],
  "chart": {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "mark": "bar",
    "encoding": {
      "x": {"field": "name", "type": "nominal"},
      "y": {"field": "revenue", "type": "quantitative"}
    },
    "data": {"values": [...]}
  },
  "metadata": {
    "row_count": 2,
    "execution_time_ms": 45,
    "truncated": false,
    "warnings": []
  }
}`}
        />

        <hr className="my-12" />

        <h2>GET /health</h2>
        <p>
          Healthcheck endpoint to verify if the API gateway is running and the database connection
          is alive.
        </p>

        <h3>Response</h3>
        <CodeBlock
          language="json"
          code={`{
  "status": "ok",
  "database": "connected",
  "version": "0.1.0"
}`}
        />
      </div>
    </div>
  );
}
