import { buildResultsCsv } from '@seal/chart-csv';

export { chartExportFilename } from '@seal/chart-csv';
export { hasVegaLiteSpec, isRenderableVegaChart } from '@seal/chart-spec';

/** Minimal Vega view surface used for client-side chart export. */
export interface VegaChartView {
  toImageURL: (type: 'png' | 'svg') => Promise<string>;
  toSVG: () => Promise<string>;
}

export type ChartImageFormat = 'png' | 'svg';

const SVG_MIME = 'image/svg+xml;charset=utf-8';
const CSV_MIME = 'text/csv;charset=utf-8';
const DEFAULT_METRIC_EXPORT_WIDTH = 640;
const DEFAULT_METRIC_EXPORT_HEIGHT = 360;

function triggerDownload(href: string, filename: string): void {
  const anchor = document.createElement('a');
  anchor.href = href;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  triggerDownload(url, filename);
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

function downloadDataUrl(dataUrl: string, filename: string): void {
  triggerDownload(dataUrl, filename);
}

function downloadText(content: string, mimeType: string, filename: string): void {
  downloadBlob(new Blob([content], { type: mimeType }), filename);
}

function escapeXml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('Failed to load image for export'));
    img.src = url;
  });
}

export function buildMetricCardSvg(
  label: string,
  value: string,
  width = DEFAULT_METRIC_EXPORT_WIDTH,
  height = DEFAULT_METRIC_EXPORT_HEIGHT,
): string {
  const safeLabel = escapeXml(label);
  const safeValue = escapeXml(value);
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="100%" height="100%" fill="#fffbeb" stroke="#f59e0b" stroke-opacity="0.35" stroke-width="2" stroke-dasharray="8 4" rx="12"/>
  <text x="50%" y="42%" text-anchor="middle" font-family="system-ui, sans-serif" font-size="14" fill="#737373" letter-spacing="0.12em">${safeLabel.toUpperCase()}</text>
  <text x="50%" y="58%" text-anchor="middle" font-family="system-ui, sans-serif" font-size="48" font-weight="600" fill="#171717">${safeValue}</text>
</svg>`;
}

async function exportSvgAsPng(svg: string, filename: string): Promise<void> {
  const blob = new Blob([svg], { type: SVG_MIME });
  const url = URL.createObjectURL(blob);
  try {
    const img = await loadImage(url);
    const canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth || DEFAULT_METRIC_EXPORT_WIDTH;
    canvas.height = img.naturalHeight || DEFAULT_METRIC_EXPORT_HEIGHT;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      throw new Error('Canvas not supported');
    }
    ctx.drawImage(img, 0, 0);
    downloadDataUrl(canvas.toDataURL('image/png'), filename);
  } finally {
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  }
}

export function exportResultsCsv(
  results: ReadonlyArray<Record<string, unknown>>,
  filename: string,
): void {
  const csv = buildResultsCsv(results);
  if (!csv) {
    return;
  }
  downloadBlob(new Blob([`\uFEFF${csv}`], { type: CSV_MIME }), filename);
}

export async function exportVegaImage(
  view: VegaChartView,
  format: ChartImageFormat,
  filename: string,
): Promise<void> {
  if (format === 'png') {
    downloadDataUrl(await view.toImageURL('png'), filename);
    return;
  }
  downloadText(await view.toSVG(), SVG_MIME, filename);
}

export async function exportMetricCardImage(
  label: string,
  value: string,
  format: ChartImageFormat,
  filename: string,
): Promise<void> {
  const svg = buildMetricCardSvg(label, value);
  if (format === 'png') {
    await exportSvgAsPng(svg, filename);
    return;
  }
  downloadText(svg, SVG_MIME, filename);
}

export function isVegaChartView(value: unknown): value is VegaChartView {
  if (!value || typeof value !== 'object') {
    return false;
  }
  const candidate = value as Partial<VegaChartView>;
  return typeof candidate.toImageURL === 'function' && typeof candidate.toSVG === 'function';
}
