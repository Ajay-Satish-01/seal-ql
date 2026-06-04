import { describe, expect, it } from 'vitest';
import {
  buildResultsCsv,
  chartExportFilename,
  collectCsvColumns,
  escapeCsvValue,
  formatCsvCellValue,
  formatResultCell,
} from '../../../shared/chart-csv.js';

describe('formatCsvCellValue', () => {
  it('returns empty string for nullish values', () => {
    expect(formatCsvCellValue(null)).toBe('');
    expect(formatCsvCellValue(undefined)).toBe('');
  });

  it('stringifies objects as JSON', () => {
    expect(formatCsvCellValue({ a: 1 })).toBe('{"a":1}');
    expect(formatCsvCellValue([1, 2])).toBe('[1,2]');
  });

  it('stringifies scalars', () => {
    expect(formatCsvCellValue(42)).toBe('42');
    expect(formatCsvCellValue('hello')).toBe('hello');
  });
});

describe('formatResultCell', () => {
  it('uses a display placeholder for nullish values', () => {
    expect(formatResultCell(null)).toBe('—');
    expect(formatResultCell(undefined, 'n/a')).toBe('n/a');
  });
});

describe('escapeCsvValue', () => {
  it('quotes values with commas or newlines', () => {
    expect(escapeCsvValue('a,b')).toBe('"a,b"');
    expect(escapeCsvValue('line\nbreak')).toBe('"line\nbreak"');
  });

  it('prefixes spreadsheet formula characters', () => {
    expect(escapeCsvValue('=1+1')).toBe("'=1+1");
    expect(escapeCsvValue('+1234')).toBe("'+1234");
    expect(escapeCsvValue('-100')).toBe("'-100");
    expect(escapeCsvValue('@SUM(A1)')).toBe("'@SUM(A1)");
  });

  it('quotes formula-prefixed values that also contain commas', () => {
    expect(escapeCsvValue('=cmd|"/c calc"!A0')).toBe('"\'=cmd|""/c calc""!A0"');
  });
});

describe('collectCsvColumns', () => {
  it('unions keys from all rows in first-seen order', () => {
    const columns = collectCsvColumns([
      { a: 1, b: 2 },
      { b: 3, c: 4 },
      { a: 5, d: 6 },
    ]);
    expect(columns).toEqual(['a', 'b', 'c', 'd']);
  });
});

describe('buildResultsCsv', () => {
  it('includes sparse columns from later rows', () => {
    const csv = buildResultsCsv([
      { month: 'Jan', total: 10 },
      { month: 'Feb', total: 20, note: 'peak' },
    ]);
    expect(csv).toBe('month,total,note\nJan,10,\nFeb,20,peak');
  });

  it('returns empty string for empty results', () => {
    expect(buildResultsCsv([])).toBe('');
  });
});

describe('chartExportFilename', () => {
  it('sanitizes chart type and extension', () => {
    const filename = chartExportFilename('Bar Chart!', 'png');
    expect(filename).toMatch(/^seal-bar_chart-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.png$/);
  });
});
