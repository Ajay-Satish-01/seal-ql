export const NON_VEGA_CHART_TYPES = ['table', 'metric_card'] as const;

export type NonVegaChartType = (typeof NON_VEGA_CHART_TYPES)[number];

export interface ChartSpecLike {
  chart_type: string;
  vega_lite_spec?: Record<string, unknown> | null;
  metadata?: Record<string, unknown> | null;
}

export function isNonVegaChartType(chartType: string): chartType is NonVegaChartType {
  return (NON_VEGA_CHART_TYPES as readonly string[]).includes(chartType);
}

export function hasVegaLiteSpec(
  vegaLiteSpec: Record<string, unknown> | null | undefined,
): boolean {
  return !!vegaLiteSpec && Object.keys(vegaLiteSpec).length > 0;
}

export function isRenderableVegaChart(
  chart: ChartSpecLike | null | undefined,
): chart is ChartSpecLike {
  if (!chart) {
    return false;
  }
  return !isNonVegaChartType(chart.chart_type) && hasVegaLiteSpec(chart.vega_lite_spec);
}

export function getChartMetadata(chart: ChartSpecLike): Record<string, unknown> {
  return chart.metadata && typeof chart.metadata === 'object' ? chart.metadata : {};
}

export function getChartYField(chart: ChartSpecLike): string | undefined {
  const yField = getChartMetadata(chart).y_field;
  return typeof yField === 'string' ? yField : undefined;
}

export interface MetricSnapshot {
  field: string;
  label: string;
  displayValue: string;
}

export function resolveMetricSnapshot(
  results: ReadonlyArray<Record<string, unknown>>,
  yField?: string,
): MetricSnapshot | null {
  if (results.length === 0) {
    return null;
  }
  const field = yField ?? Object.keys(results[0] ?? {})[0];
  if (!field) {
    return null;
  }
  const raw = results[0]?.[field];
  return {
    field,
    label: field.replace(/_/g, ' '),
    displayValue: raw != null ? String(raw) : '—',
  };
}
