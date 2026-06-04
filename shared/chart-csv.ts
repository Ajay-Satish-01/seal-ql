const CSV_FORMULA_PREFIX = /^[=+\-@\t|]/;

/** Format a query cell for CSV export. */
export function formatCsvCellValue(value: unknown): string {
  if (value == null) {
    return '';
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

/** Escape a single CSV field, including spreadsheet formula injection guards. */
export function escapeCsvValue(value: unknown): string {
  let text = formatCsvCellValue(value);
  if (CSV_FORMULA_PREFIX.test(text)) {
    text = `'${text}`;
  }
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

/** Format a result cell for on-screen tables (uses the same rules as CSV export). */
export function formatResultCell(value: unknown, empty = '—'): string {
  if (value == null) {
    return empty;
  }
  return formatCsvCellValue(value);
}

/** Collect column names from all rows, preserving first-seen order. */
export function collectCsvColumns(
  results: ReadonlyArray<Record<string, unknown>>,
): string[] {
  const columns: string[] = [];
  const seen = new Set<string>();
  for (const row of results) {
    for (const key of Object.keys(row)) {
      if (!seen.has(key)) {
        seen.add(key);
        columns.push(key);
      }
    }
  }
  return columns;
}

/** Build CSV text for query results. */
export function buildResultsCsv(results: ReadonlyArray<Record<string, unknown>>): string {
  if (results.length === 0) {
    return '';
  }
  const columns = collectCsvColumns(results);
  const lines = [
    columns.join(','),
    ...results.map((row) => columns.map((col) => escapeCsvValue(row[col])).join(',')),
  ];
  return lines.join('\n');
}

export function chartExportFilename(chartType: string, extension: string): string {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const safeType =
    chartType
      .replace(/[^a-z0-9_-]+/gi, '_')
      .replace(/_+/g, '_')
      .replace(/^_|_$/g, '')
      .toLowerCase() || 'chart';
  return `seal-${safeType}-${stamp}.${extension}`;
}
