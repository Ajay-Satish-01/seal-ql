import { describe, expect, it } from 'vitest';
import {
  getChartYField,
  hasVegaLiteSpec,
  isNonVegaChartType,
  isRenderableVegaChart,
  resolveMetricSnapshot,
} from '../../../shared/chart-spec.js';

describe('hasVegaLiteSpec', () => {
  it('returns false for empty specs', () => {
    expect(hasVegaLiteSpec(undefined)).toBe(false);
    expect(hasVegaLiteSpec({})).toBe(false);
  });

  it('returns true when keys exist', () => {
    expect(hasVegaLiteSpec({ mark: 'bar' })).toBe(true);
  });
});

describe('isNonVegaChartType', () => {
  it('identifies table and metric_card', () => {
    expect(isNonVegaChartType('table')).toBe(true);
    expect(isNonVegaChartType('metric_card')).toBe(true);
    expect(isNonVegaChartType('bar')).toBe(false);
  });
});

describe('isRenderableVegaChart', () => {
  it('requires a non-table chart with Vega-Lite data', () => {
    expect(
      isRenderableVegaChart({
        chart_type: 'bar',
        vega_lite_spec: { mark: 'bar' },
      }),
    ).toBe(true);
    expect(
      isRenderableVegaChart({
        chart_type: 'table',
        vega_lite_spec: { mark: 'bar' },
      }),
    ).toBe(false);
    expect(
      isRenderableVegaChart({
        chart_type: 'bar',
        vega_lite_spec: {},
      }),
    ).toBe(false);
  });
});

describe('getChartYField', () => {
  it('reads y_field from metadata', () => {
    expect(getChartYField({ chart_type: 'metric_card', metadata: { y_field: 'total' } })).toBe(
      'total',
    );
    expect(getChartYField({ chart_type: 'metric_card', metadata: { y_field: 1 } })).toBeUndefined();
  });
});

describe('resolveMetricSnapshot', () => {
  it('uses y_field when provided', () => {
    expect(resolveMetricSnapshot([{ total: 42, other: 1 }], 'total')).toEqual({
      field: 'total',
      label: 'total',
      displayValue: '42',
    });
  });

  it('returns null for empty results', () => {
    expect(resolveMetricSnapshot([])).toBeNull();
  });
});
