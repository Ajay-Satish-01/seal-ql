export const CHART_TEMPLATES = [
  { id: 'default', label: 'Default', description: 'Standard axes and title styling.' },
  { id: 'minimal', label: 'Minimal', description: 'Clean look with no grid lines or axis domain.' },
  { id: 'bold', label: 'Bold', description: 'Larger title and axis labels.' },
  { id: 'rounded', label: 'Rounded', description: 'Rounded bar corners with standard axes.' },
] as const;

export const CHART_COLOR_SCHEMES = [
  {
    id: 'category10',
    label: 'Category 10',
    swatches: ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
  },
  {
    id: 'tableau10',
    label: 'Tableau 10',
    swatches: ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f'],
  },
  {
    id: 'set2',
    label: 'Set 2',
    swatches: ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854'],
  },
  {
    id: 'viridis',
    label: 'Viridis',
    swatches: ['#440154', '#3b528b', '#21918c', '#5ec962', '#fde725'],
  },
  {
    id: 'blues',
    label: 'Blues',
    swatches: ['#c6dbef', '#6baed6', '#3182bd', '#08519c', '#08306b'],
  },
  {
    id: 'oranges',
    label: 'Oranges',
    swatches: ['#fdd0a2', '#fdae6b', '#fd8d3c', '#e6550d', '#a63603'],
  },
] as const;

export type ChartTemplateId = (typeof CHART_TEMPLATES)[number]['id'];
export type ChartColorSchemeId = (typeof CHART_COLOR_SCHEMES)[number]['id'];

export interface ChartStyleSelection {
  template: ChartTemplateId;
  color_scheme: ChartColorSchemeId;
}

export const DEFAULT_CHART_STYLE: ChartStyleSelection = {
  template: 'default',
  color_scheme: 'category10',
};

const TEMPLATE_CONFIGS: Record<ChartTemplateId, Record<string, unknown>> = {
  default: {},
  minimal: {
    axis: { grid: false, domain: false },
    view: { stroke: 'transparent' },
  },
  bold: {
    title: { fontSize: 16, fontWeight: 'bold' },
    axis: { labelFontSize: 12, titleFontSize: 13 },
  },
  rounded: {},
};

const TEMPLATE_MARK: Partial<Record<ChartTemplateId, Record<string, unknown>>> = {
  rounded: { cornerRadiusEnd: 4 },
};

function deepMerge(
  base: Record<string, unknown>,
  overlay: Record<string, unknown>,
): Record<string, unknown> {
  const merged = { ...base };
  for (const [key, value] of Object.entries(overlay)) {
    const existing = merged[key];
    if (
      existing &&
      typeof existing === 'object' &&
      !Array.isArray(existing) &&
      typeof value === 'object' &&
      value !== null &&
      !Array.isArray(value)
    ) {
      merged[key] = deepMerge(existing as Record<string, unknown>, value as Record<string, unknown>);
    } else {
      merged[key] = value;
    }
  }
  return merged;
}

export function getSchemeSwatches(schemeId: ChartColorSchemeId): readonly string[] {
  const scheme = CHART_COLOR_SCHEMES.find((s) => s.id === schemeId);
  return scheme?.swatches ?? CHART_COLOR_SCHEMES[0].swatches;
}

export function getSchemePrimaryColor(schemeId: ChartColorSchemeId): string {
  return getSchemeSwatches(schemeId)[0] ?? '#1f77b4';
}

interface StyleContext {
  chartType: string;
  xField?: string;
  colorField?: string;
}

function resolveStyleContext(
  chartType: string,
  metadata?: Record<string, unknown> | null,
): StyleContext {
  const meta = metadata && typeof metadata === 'object' ? metadata : {};
  return {
    chartType,
    xField: typeof meta.x_field === 'string' ? meta.x_field : undefined,
    colorField: typeof meta.color_field === 'string' ? meta.color_field : undefined,
  };
}

/** Strip style overlay from a base Vega-Lite spec (keeps data, encodings, mark type). */
export function stripChartStyle(spec: Record<string, unknown>): Record<string, unknown> {
  const base = structuredClone(spec);
  delete base.config;

  const mark = base.mark;
  if (mark && typeof mark === 'object' && !Array.isArray(mark)) {
    const { cornerRadiusEnd: _c, ...rest } = mark as Record<string, unknown>;
    base.mark = rest;
  }

  const encoding = base.encoding;
  if (encoding && typeof encoding === 'object' && !Array.isArray(encoding)) {
    const enc = { ...(encoding as Record<string, unknown>) };
    const color = enc.color;
    if (color && typeof color === 'object' && !Array.isArray(color)) {
      const colorEnc = { ...(color as Record<string, unknown>) };
      if ('value' in colorEnc) {
        delete enc.color;
      } else {
        delete colorEnc.scale;
        enc.color = colorEnc;
      }
    }
    base.encoding = enc;
  }

  return base;
}

export function applyChartStyleClient(
  spec: Record<string, unknown>,
  style: ChartStyleSelection,
  context: StyleContext,
): Record<string, unknown> {
  if (!spec || Object.keys(spec).length === 0) {
    return spec;
  }

  const styled = stripChartStyle(structuredClone(spec));
  const scheme = style.color_scheme;
  const primaryColor = getSchemePrimaryColor(scheme);

  const templateConfig = TEMPLATE_CONFIGS[style.template];
  if (Object.keys(templateConfig).length > 0) {
    styled.config = deepMerge(
      (styled.config as Record<string, unknown> | undefined) ?? {},
      templateConfig,
    );
  }

  const markOverlay = TEMPLATE_MARK[style.template];
  if (markOverlay && styled.mark && typeof styled.mark === 'object' && !Array.isArray(styled.mark)) {
    const markType = (styled.mark as Record<string, unknown>).type;
    if (markType === 'bar') {
      styled.mark = deepMerge(styled.mark as Record<string, unknown>, markOverlay);
    }
  }

  const encoding = { ...((styled.encoding as Record<string, unknown> | undefined) ?? {}) };
  const { chartType, xField } = context;

  if (chartType === 'pie') {
    const colorEnc = encoding.color;
    if (colorEnc && typeof colorEnc === 'object' && !Array.isArray(colorEnc) && 'field' in colorEnc) {
      encoding.color = {
        ...(colorEnc as Record<string, unknown>),
        scale: { scheme },
      };
    }
  } else if (chartType === 'bar') {
    const colorEnc = encoding.color;
    if (
      colorEnc &&
      typeof colorEnc === 'object' &&
      !Array.isArray(colorEnc) &&
      typeof (colorEnc as Record<string, unknown>).field === 'string'
    ) {
      encoding.color = {
        ...(colorEnc as Record<string, unknown>),
        scale: { scheme },
      };
    } else if (xField) {
      const xEnc = encoding.x;
      const xType =
        xEnc && typeof xEnc === 'object' && !Array.isArray(xEnc)
          ? (xEnc as Record<string, unknown>).type
          : undefined;
      if (xType === 'nominal') {
        encoding.color = {
          field: xField,
          type: 'nominal',
          scale: { scheme },
        };
      }
    }
  } else if (chartType === 'line' || chartType === 'area' || chartType === 'scatter') {
    const colorEnc = encoding.color;
    if (
      colorEnc &&
      typeof colorEnc === 'object' &&
      !Array.isArray(colorEnc) &&
      typeof (colorEnc as Record<string, unknown>).field === 'string'
    ) {
      encoding.color = {
        ...(colorEnc as Record<string, unknown>),
        scale: { scheme },
      };
    } else {
      encoding.color = { value: primaryColor };
    }
  }

  if (Object.keys(encoding).length > 0) {
    styled.encoding = encoding;
  }

  return styled;
}

export function stylesMatch(a: ChartStyleSelection, b: ChartStyleSelection): boolean {
  return a.template === b.template && a.color_scheme === b.color_scheme;
}

export function formatChartStyleLabel(style: ChartStyleSelection): string {
  const template =
    CHART_TEMPLATES.find((entry) => entry.id === style.template)?.label ?? style.template;
  const scheme =
    CHART_COLOR_SCHEMES.find((entry) => entry.id === style.color_scheme)?.label ??
    style.color_scheme;
  return `${template} · ${scheme}`;
}

/** True when the picker style differs from what the API stored on chart.metadata. */
export function isClientStylePreview(
  chartStyle: ChartStyleSelection | undefined,
  metadata?: Record<string, unknown> | null,
): boolean {
  if (!chartStyle) {
    return false;
  }
  if (!metadataHasStyle(metadata)) {
    return true;
  }
  return !stylesMatch(chartStyle, chartStyleFromMetadata(metadata));
}

export function metadataHasStyle(metadata?: Record<string, unknown> | null): boolean {
  const meta = metadata && typeof metadata === 'object' ? metadata : {};
  const template = meta.template;
  const colorScheme = meta.color_scheme;
  return (
    typeof template === 'string' &&
    typeof colorScheme === 'string' &&
    CHART_TEMPLATES.some((t) => t.id === template) &&
    CHART_COLOR_SCHEMES.some((s) => s.id === colorScheme)
  );
}

export function applyChartStyleToSpec(
  chart: {
    chart_type: string;
    vega_lite_spec?: Record<string, unknown> | null;
    metadata?: Record<string, unknown> | null;
  },
  style: ChartStyleSelection,
): Record<string, unknown> | null | undefined {
  const spec = chart.vega_lite_spec;
  if (!spec || Object.keys(spec).length === 0) {
    return spec;
  }
  const context = resolveStyleContext(chart.chart_type, chart.metadata);
  return applyChartStyleClient(spec, style, context);
}

/**
 * Use the server-styled Vega spec when it already matches the active selection;
 * otherwise apply (or re-apply) style client-side for picker overrides.
 */
export function resolveStyledChartSpec(
  chart: {
    chart_type: string;
    vega_lite_spec?: Record<string, unknown> | null;
    metadata?: Record<string, unknown> | null;
  },
  chartStyle?: ChartStyleSelection,
): Record<string, unknown> | null | undefined {
  const spec = chart.vega_lite_spec;
  if (!spec || Object.keys(spec).length === 0) {
    return spec;
  }

  const metaStyle = chartStyleFromMetadata(chart.metadata);
  const activeStyle = chartStyle ?? metaStyle;

  if (metadataHasStyle(chart.metadata) && stylesMatch(activeStyle, metaStyle)) {
    return spec;
  }
  if (!metadataHasStyle(chart.metadata) && chartStyle === undefined) {
    return spec;
  }

  return applyChartStyleToSpec(chart, activeStyle);
}

export function chartStyleFromMetadata(
  metadata?: Record<string, unknown> | null,
): ChartStyleSelection {
  const meta = metadata && typeof metadata === 'object' ? metadata : {};
  const template = meta.template;
  const colorScheme = meta.color_scheme;
  return {
    template:
      typeof template === 'string' &&
      CHART_TEMPLATES.some((t) => t.id === template)
        ? (template as ChartTemplateId)
        : DEFAULT_CHART_STYLE.template,
    color_scheme:
      typeof colorScheme === 'string' &&
      CHART_COLOR_SCHEMES.some((s) => s.id === colorScheme)
        ? (colorScheme as ChartColorSchemeId)
        : DEFAULT_CHART_STYLE.color_scheme,
  };
}
