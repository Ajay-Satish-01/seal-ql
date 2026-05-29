import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';
import { VegaChart } from '../src/react.js';
import type { ChartSpec } from '../src/types.js';

// Mock vega-embed so it doesn't actually try to render in jsdom
vi.mock('vega-embed', () => ({
  default: vi.fn().mockResolvedValue({
    view: {
      finalize: vi.fn(),
    },
  }),
}));

describe('VegaChart', () => {
  it('renders null for table chart type', () => {
    const spec: ChartSpec = {
      chart_type: 'table',
      vega_lite_spec: {},
      metadata: {},
    };
    const { container } = render(<VegaChart spec={spec} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders null for metric_card chart type', () => {
    const spec: ChartSpec = {
      chart_type: 'metric_card',
      vega_lite_spec: {},
      metadata: {},
    };
    const { container } = render(<VegaChart spec={spec} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders a div container for standard charts', () => {
    const spec: ChartSpec = {
      chart_type: 'bar',
      vega_lite_spec: {
        $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
        mark: 'bar',
      },
      metadata: {},
    };
    const { container } = render(<VegaChart spec={spec} />);
    const div = container.firstChild as HTMLDivElement;
    expect(div).not.toBeNull();
    expect(div.className).toContain('intelligence-vega-chart');
  });
});
