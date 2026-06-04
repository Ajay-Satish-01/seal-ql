'use client';

import dynamic from 'next/dynamic';
import { useTheme } from 'next-themes';
import { memo, useCallback, useEffect, useRef, type RefObject } from 'react';
import type { ChartSpec } from 'seal';
import { collectCsvColumns, formatResultCell } from '@seal/chart-csv';
import { getChartYField, isRenderableVegaChart, resolveMetricSnapshot } from '@seal/chart-spec';
import { ChartExportMenu } from '@/components/dashboard/chart-export-menu';
import { Badge } from '@/components/ui/badge';
import { isVegaChartView, type VegaChartView } from '@/lib/chart-export';

const CHART_HEIGHT_CLASS = 'h-[360px]';
const EMPTY_STATE_HEIGHT_CLASS = 'h-[200px]';

const VegaChart = dynamic(() => import('seal').then((m) => m.VegaChart), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});

function ChartSkeleton() {
  return (
    <div
      className={`bg-muted/40 flex ${CHART_HEIGHT_CLASS} animate-pulse items-center justify-center rounded-lg`}
    >
      <span className="text-muted-foreground text-sm">Rendering chart…</span>
    </div>
  );
}

function EmptyChartState({ message }: { message: string }) {
  return (
    <div
      className={`text-muted-foreground flex ${EMPTY_STATE_HEIGHT_CLASS} items-center justify-center rounded-lg border border-dashed`}
    >
      {message}
    </div>
  );
}

interface ChartPanelProps {
  chart: ChartSpec | null;
  results: Record<string, unknown>[];
}

function ChartPanelHeader({
  chartType,
  results,
  vegaViewRef,
  canExportVegaImages,
  metricSnapshot,
}: {
  chartType: string;
  results: Record<string, unknown>[];
  vegaViewRef: RefObject<VegaChartView | null>;
  canExportVegaImages: boolean;
  metricSnapshot?: ReturnType<typeof resolveMetricSnapshot>;
}) {
  return (
    <div className="flex items-center gap-2">
      <Badge variant="outline" className="font-mono text-xs uppercase">
        {chartType}
      </Badge>
      <ChartExportMenu
        chartType={chartType}
        results={results}
        vegaViewRef={vegaViewRef}
        canExportVegaImages={canExportVegaImages}
        metricSnapshot={metricSnapshot}
      />
    </div>
  );
}

function MetricCard({
  snapshot,
}: {
  snapshot: NonNullable<ReturnType<typeof resolveMetricSnapshot>>;
}) {
  return (
    <div
      className={`flex ${CHART_HEIGHT_CLASS} flex-col items-center justify-center rounded-lg border border-dashed border-amber-500/30 bg-amber-500/5`}
    >
      <span className="text-muted-foreground mb-2 text-xs font-medium tracking-widest uppercase">
        {snapshot.label}
      </span>
      <span className="text-5xl font-semibold tabular-nums">{snapshot.displayValue}</span>
    </div>
  );
}

function ResultsTable({ results }: { results: Record<string, unknown>[] }) {
  if (results.length === 0) {
    return <p className="text-muted-foreground text-sm">No rows returned.</p>;
  }

  const columns = collectCsvColumns(results);
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
                  {formatResultCell(row[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export const ChartPanel = memo(function ChartPanel({ chart, results }: ChartPanelProps) {
  const { resolvedTheme } = useTheme();
  const vegaViewRef = useRef<VegaChartView | null>(null);
  const vegaTheme = resolvedTheme === 'dark' ? 'dark' : 'light';

  const handleVegaRender = useCallback((view: unknown) => {
    if (view == null) {
      vegaViewRef.current = null;
      return;
    }
    vegaViewRef.current = isVegaChartView(view) ? view : null;
  }, []);

  useEffect(() => {
    vegaViewRef.current = null;
  }, [chart, vegaTheme]);

  if (!chart) {
    return results.length > 0 ? (
      <div className="space-y-3">
        <ChartPanelHeader
          chartType="table"
          results={results}
          vegaViewRef={vegaViewRef}
          canExportVegaImages={false}
        />
        <ResultsTable results={results} />
      </div>
    ) : (
      <EmptyChartState message="No chart or rows yet." />
    );
  }

  const chartType = chart.chart_type;
  const yField = getChartYField(chart);
  const metricSnapshot = resolveMetricSnapshot(results, yField);
  const canExportVegaImages = isRenderableVegaChart(chart);

  return (
    <div className="space-y-3">
      <ChartPanelHeader
        chartType={chartType}
        results={results}
        vegaViewRef={vegaViewRef}
        canExportVegaImages={canExportVegaImages}
        metricSnapshot={metricSnapshot}
      />

      {chartType === 'table' ? (
        <ResultsTable results={results} />
      ) : chartType === 'metric_card' ? (
        metricSnapshot ? (
          <MetricCard snapshot={metricSnapshot} />
        ) : (
          <EmptyChartState message="No metric value returned." />
        )
      ) : canExportVegaImages ? (
        <div className={`${CHART_HEIGHT_CLASS} w-full`}>
          <VegaChart
            spec={chart}
            theme={vegaTheme}
            className="h-full w-full"
            onRender={handleVegaRender}
          />
        </div>
      ) : (
        <EmptyChartState message="Chart spec is missing Vega-Lite data." />
      )}
    </div>
  );
});
