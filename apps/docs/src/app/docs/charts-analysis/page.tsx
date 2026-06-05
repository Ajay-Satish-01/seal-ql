import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { ParamTable } from '@/components/docs/param-table';

export default function ChartsAnalysisPage() {
  return (
    <div className="w-full">
      <PageHeader
        title="Charts & Analysis"
        description="How Seal chooses chart types and returns Vega-Lite specs."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <p>
          Every <code>POST /v1/query</code> response may include a <code>chart</code> object. The
          chart engine applies heuristics on top of the planner&apos;s suggestion (e.g. pie → bar
          for many categories).
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">chart_type values</h2>
        <ParamTable
          rows={[
            {
              name: 'bar, line, pie, scatter, area',
              type: 'ChartSpec',
              description: 'Full vega_lite_spec — render with VegaChart or vega-embed.',
            },
            {
              name: 'table',
              type: 'ChartSpec',
              description: 'vega_lite_spec is {} — render results as a data grid.',
            },
            {
              name: 'metric_card',
              type: 'ChartSpec',
              description:
                'Single KPI from results; use chart.metadata.y_field for the value column.',
            },
          ]}
        />

        <h2 className="text-foreground mt-10 text-2xl font-bold">ChartSpec shape</h2>
        <CodeBlock
          language="json"
          code={`{
  "chart_type": "bar",
  "vega_lite_spec": {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "data": { "values": [...] },
    "mark": { "type": "bar", "tooltip": true },
    "encoding": { ... }
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

        <h2 className="text-foreground mt-10 text-2xl font-bold">Custom UI libraries</h2>
        <p>
          You can ignore Vega and chart from <code>results</code> + <code>columns</code> using{' '}
          <code>metadata.x_field</code> / <code>y_field</code> hints. The SQL and rows are always
          authoritative.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">See it live</h2>
        <p>
          <Link href="/demo">Interactive demo</Link> — preset queries with bar, line, pie, table,
          metric, and scatter outputs.
        </p>
      </div>
    </div>
  );
}
