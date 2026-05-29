import { PageHeader } from "@/components/page-header";
import { CodeBlock } from "@/components/code-block";

export default function ChartsAnalysisPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Charts & Analysis"
        description="Visualize your database results automatically in your frontend."
      />

      <div className="prose prose-slate dark:prose-invert max-w-none text-muted-foreground leading-relaxed">

        <p>
          Intelligence Connector does more than just return raw database rows. For every successful query, the Gateway's Chart Engine analyzes the shape of the result set and automatically generates a complete <strong>Vega-Lite JSON schema</strong>.
        </p>

        <p>
          Because we return raw SQL results alongside an industry-standard Vega-Lite schema, you have two flexible options for rendering charts in your application:
        </p>

        <hr />

        <h2>Option 1: Using Vega-Lite (Recommended)</h2>
        <p>
          Vega-Lite is a high-level grammar of interactive graphics. If you use React, the easiest way to render our generated charts is using the <code>react-vega</code> library.
        </p>

        <h3>1. Install the dependencies</h3>
        <CodeBlock language="bash" code="npm install react-vega vega vega-lite" />

        <h3>2. Render the chart</h3>
        <p>You can directly pass the <code>chart</code> object returned from the API into the <code>VegaLite</code> component.</p>
        <CodeBlock language="tsx" code={`import React, { useState } from 'react';
import { VegaLite } from 'react-vega';

export function DataDashboard() {
  const [data, setData] = useState(null);

  const askQuestion = async () => {
    const res = await fetch("http://localhost:8000/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "Revenue by month for the last year" })
    });

    const json = await res.json();
    setData(json);
  };

  return (
    <div>
      <button onClick={askQuestion}>Ask Question</button>

      {data && data.chart && (
        <div className="chart-container">
          {/* Render the Vega-Lite chart instantly */}
          <VegaLite spec={data.chart} />
        </div>
      )}
    </div>
  );
}`} />


        <hr />

        <h2>Option 2: Using Custom Charting Libraries</h2>
        <p>
          Because the <code>/query</code> API also returns the exact <code>columns</code> and <code>results</code> arrays, you are not locked into Vega-Lite. You can easily map the raw data into any charting library like <strong>Recharts</strong>, <strong>Chart.js</strong>, or <strong>Tremor</strong>.
        </p>

        <h3>Example: Recharts Integration</h3>
        <CodeBlock language="bash" code="npm install recharts" />

        <CodeBlock language="tsx" code={`import { BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';

export function CustomRechartsDisplay({ data }) {
  // data.results looks like: [{ month: "Jan", revenue: 100 }, { month: "Feb", revenue: 200 }]

  return (
    <BarChart width={600} height={300} data={data.results}>
      <XAxis dataKey={data.columns[0]} /> {/* e.g. "month" */}
      <YAxis />
      <Tooltip />
      <Bar dataKey={data.columns[1]} fill="#8884d8" /> {/* e.g. "revenue" */}
    </BarChart>
  );
}`} />

        <p className="mt-8">
          This flexibility allows you to rapidly prototype with Vega-Lite's automatic configurations, and later build deeply integrated, highly-customized dashboards using your library of choice.
        </p>

      </div>
    </div>
  );
}
