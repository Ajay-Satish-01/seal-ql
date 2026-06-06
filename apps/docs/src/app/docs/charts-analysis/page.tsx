import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { Callout } from '@/components/docs/callout';
import { DocsProse } from '@/components/docs/docs-prose';
import { ParamTable } from '@/components/docs/param-table';
import { SITE } from '@/lib/constants';
// Schema URL in inline JSON examples below must stay aligned with VEGA_LITE_SCHEMA from 'seal'.

export default function ChartsAnalysisPage() {
  const base = SITE.defaultBaseUrl;

  return (
    <div className="w-full">
      <PageHeader
        title="Charts & Analysis"
        description="How Seal chooses chart types, returns Vega-Lite specs, and how to render them."
      />

      <DocsProse>
        <p>
          Every <code>POST /v1/query</code> response includes a <code>chart</code> object with a
          Vega-Lite specification. On <code>POST /v1/chat</code>, charts are opt-in via{' '}
          <code>include_charts: true</code>. The chart engine is <strong>heuristic</strong> — it
          inspects result column types and row count to pick an appropriate visualization without
          an extra LLM call.
        </p>

        <Callout variant="info" title="No extra LLM cost">
          Chart generation uses rule-based heuristics on top of the planner&apos;s column
          suggestion — no separate chart model call. The engine may override the planner&apos;s
          pick (e.g. pie → bar when there are too many categories).
        </Callout>

        <h2>Chart selection logic</h2>
        <p>The engine evaluates result shape and decides:</p>
        <ul>
          <li>
            <strong>1 row, 1 numeric column</strong> → <code>metric_card</code> (single KPI display)
          </li>
          <li>
            <strong>Categorical × numeric</strong> → <code>bar</code> (or <code>pie</code> for ≤6
            categories)
          </li>
          <li>
            <strong>Time series × numeric</strong> → <code>line</code> (or <code>area</code> for
            cumulative data)
          </li>
          <li>
            <strong>Two numeric columns</strong> → <code>scatter</code>
          </li>
          <li>
            <strong>Many columns / no clear pattern</strong> → <code>table</code> (data grid)
          </li>
        </ul>
        <p>
          The planner suggests a chart type in <code>QueryPlan</code>; the engine may override it
          based on actual result data. <code>chart.metadata.requested_chart_type</code> shows the
          planner&apos;s suggestion, and <code>applied_chart_type</code> shows what actually
          rendered.
        </p>

        <h2>chart_type values</h2>
        <ParamTable
          rows={[
            {
              name: 'bar',
              type: 'ChartSpec',
              description:
                'Vertical bars — categorical x-axis, numeric y-axis. Full vega_lite_spec provided.',
            },
            {
              name: 'line',
              type: 'ChartSpec',
              description:
                'Time series or sequential data. Full vega_lite_spec with temporal x-encoding.',
            },
            {
              name: 'area',
              type: 'ChartSpec',
              description: 'Filled area variant of line chart for cumulative data.',
            },
            {
              name: 'pie',
              type: 'ChartSpec',
              description: 'Proportional split — used for ≤6 categories.',
            },
            {
              name: 'scatter',
              type: 'ChartSpec',
              description: 'Two numeric axes — correlation or distribution.',
            },
            {
              name: 'table',
              type: 'ChartSpec',
              description:
                'vega_lite_spec is {} — render results as a data grid using columns and results.',
            },
            {
              name: 'metric_card',
              type: 'ChartSpec',
              description:
                'Single KPI value. Use chart.metadata.y_field for the value column name.',
            },
          ]}
        />

        <h2>ChartSpec shape</h2>
        <CodeBlock
          language="json"
          code={`{
  "chart_type": "bar",
  "vega_lite_spec": {
    "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
    "data": { "values": [
      { "category": "Electronics", "total_revenue": 45200 },
      { "category": "Clothing", "total_revenue": 32100 },
      { "category": "Books", "total_revenue": 18700 }
    ] },
    "mark": { "type": "bar", "tooltip": true },
    "encoding": {
      "x": { "field": "category", "type": "nominal" },
      "y": { "field": "total_revenue", "type": "quantitative" }
    }
  },
  "metadata": {
    "requested_chart_type": "bar",
    "applied_chart_type": "bar",
    "x_field": "category",
    "y_field": "total_revenue",
    "color_field": null
  }
}`}
        />

        <h2>Examples</h2>
        <h3>curl — query with chart</h3>
        <CodeBlock
          language="bash"
          code={`curl -s -X POST "${base}/v1/query" \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: your-api-key" \\
  -d '{"query":"Revenue by product category"}' \\
  | jq '{chart_type: .chart.chart_type, x: .chart.metadata.x_field, y: .chart.metadata.y_field}'`}
        />
        <CodeBlock
          language="json"
          code={`{
  "chart_type": "bar",
  "x": "category",
  "y": "total_revenue"
}`}
        />

        <h3>curl — chat with charts</h3>
        <CodeBlock
          language="bash"
          code={`curl -s -X POST "${base}/v1/chat" \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: your-api-key" \\
  -d '{"message":"Show monthly revenue trend","include_charts":true}' \\
  | jq '{chart_type: .chart.chart_type, message: .message[:80]}'`}
        />

        <h3>Python SDK</h3>
        <CodeBlock
          language="python"
          code={`from seal import Seal

with Seal("${base}", api_key="your-api-key") as client:
    result = client.query("Revenue by category")

    if result.chart:
        print(f"Chart type: {result.chart['chart_type']}")
        print(f"X field: {result.chart['metadata']['x_field']}")
        print(f"Y field: {result.chart['metadata']['y_field']}")

        # Render with any Vega-Lite library
        vega_spec = result.chart["vega_lite_spec"]

    # Chat with charts
    resp = client.chat("Monthly revenue", include_charts=True)
    if resp.chart:
        print(f"Chat chart: {resp.chart['chart_type']}")`}
        />

        <h3>TypeScript SDK (React)</h3>
        <CodeBlock
          language="tsx"
          code={`import { Seal, VegaChart } from 'seal';

const client = new Seal({
  baseUrl: '${base}',
  apiKey: 'your-api-key',
});

// Query and render
const result = await client.query('Revenue by category');

if (result.chart && result.chart.chart_type !== 'table') {
  // Render Vega-Lite chart
  <VegaChart spec={result.chart} theme="dark" actions />
} else {
  // Render as data grid using result.results + result.columns
  <DataTable columns={result.columns} rows={result.results} />
}

// Metric card handling
if (result.chart?.chart_type === 'metric_card') {
  const valueField = result.chart.metadata.y_field;
  const value = result.results[0]?.[valueField];
  // Render as a single KPI card
}`}
        />

        <h2>Custom UI libraries</h2>
        <p>
          You can ignore the Vega-Lite spec and build your own charts from <code>results</code> +{' '}
          <code>columns</code>. Use <code>chart.metadata.x_field</code> and{' '}
          <code>chart.metadata.y_field</code> as column hints. The SQL and rows are always
          authoritative — the spec is a convenience, not a requirement.
        </p>
        <CodeBlock
          language="typescript"
          code={`// Use chart metadata hints with Recharts, Chart.js, etc.
const { x_field, y_field, color_field } = result.chart.metadata;
const data = result.results.map(row => ({
  x: row[x_field],
  y: row[y_field],
  color: color_field ? row[color_field] : undefined,
}));`}
        />

        <h2>See it live</h2>
        <p>
          <Link href="/demo">Interactive demo</Link> — preset queries with bar, line, pie, table,
          metric, and scatter outputs. The operational{' '}
          <Link href="/docs/dashboard">dashboard</Link> on port 3001 renders live charts from
          your API.
        </p>
      </DocsProse>
    </div>
  );
}
