'use client';

import dynamic from 'next/dynamic';
import type { ChartSpec } from 'intelligence-sdk';
import { useTheme } from 'next-themes';
import { Badge } from '@/components/ui/badge';

const VegaChart = dynamic(() => import('intelligence-sdk').then((m) => m.VegaChart), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});

function ChartSkeleton() {
  return (
    <div className="bg-muted/40 flex h-[360px] animate-pulse items-center justify-center rounded-lg">
      <span className="text-muted-foreground text-sm">Rendering chart…</span>
    </div>
  );
}

interface ChartPanelProps {
  chart: ChartSpec | null;
  results: Record<string, unknown>[];
}

function MetricCard({ results, yField }: { results: Record<string, unknown>[]; yField?: string }) {
  const field = yField ?? Object.keys(results[0] ?? {})[0];
  const value = field ? results[0]?.[field] : null;
  return (
    <div className="flex h-[360px] flex-col items-center justify-center rounded-lg border border-dashed border-amber-500/30 bg-amber-500/5">
      <span className="text-muted-foreground mb-2 text-xs font-medium tracking-widest uppercase">
        {field?.replace(/_/g, ' ') ?? 'Metric'}
      </span>
      <span className="font-heading text-5xl font-semibold tabular-nums">
        {value != null ? String(value) : '—'}
      </span>
    </div>
  );
}

function ResultsTable({ results }: { results: Record<string, unknown>[] }) {
  if (results.length === 0) {
    return <p className="text-muted-foreground text-sm">No rows returned.</p>;
  }
  const columns = Object.keys(results[0] ?? {});
  return (
    <div className="max-h-[360px] overflow-auto rounded-lg border">
      <table className="w-full text-left text-sm">
        <thead className="bg-muted/80 sticky top-0">
          <tr>
            {columns.map((col) => (
              <th key={col} className="border-border/50 border-b px-3 py-2 font-mono text-xs">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {results.map((row, i) => (
            <tr key={i} className="border-border/30 border-b last:border-0">
              {columns.map((col) => (
                <td key={col} className="px-3 py-2 font-mono text-xs">
                  {row[col] != null ? String(row[col]) : '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ChartPanel({ chart, results }: ChartPanelProps) {
  const { resolvedTheme } = useTheme();

  if (!chart) {
    return (
      <div className="text-muted-foreground flex h-[360px] items-center justify-center rounded-lg border border-dashed">
        No chart spec — table-only response.
      </div>
    );
  }

  const chartType = chart.chart_type;
  const meta = chart.metadata as Record<string, unknown>;
  const yField = typeof meta.y_field === 'string' ? meta.y_field : undefined;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="font-mono text-xs uppercase">
          {chartType}
        </Badge>
        {meta.applied_chart_type && meta.applied_chart_type !== meta.requested_chart_type ? (
          <span className="text-muted-foreground text-xs">
            (heuristic: {String(meta.applied_chart_type)})
          </span>
        ) : null}
      </div>

      {chartType === 'table' ? (
        <ResultsTable results={results} />
      ) : chartType === 'metric_card' ? (
        <MetricCard results={results} yField={yField} />
      ) : (
        <div className="h-[360px] w-full">
          <VegaChart
            spec={chart}
            theme={resolvedTheme === 'dark' ? 'dark' : 'light'}
            className="h-full w-full"
            actions={false}
          />
        </div>
      )}
    </div>
  );
}
