import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';
import { VegaChart } from '../src/react.js';
import { VEGA_LITE_SCHEMA, type ChartSpec } from '../src/types.js';

// Mock vega-embed so it doesn't actually try to render in jsdom
const mockFinalize = vi.fn();
const mockView = { finalize: mockFinalize };

vi.mock('vega-embed', () => ({
  default: vi.fn().mockResolvedValue({
    view: mockView,
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
        $schema: VEGA_LITE_SCHEMA,
        mark: 'bar',
      },
      metadata: {},
    };
    const { container } = render(<VegaChart spec={spec} />);
    const div = container.firstChild as HTMLDivElement;
    expect(div).not.toBeNull();
    expect(div.className).toContain('seal-vega-chart');
  });

  it('calls onRender with null when the chart unmounts', async () => {
    const onRender = vi.fn();
    const spec: ChartSpec = {
      chart_type: 'bar',
      vega_lite_spec: {
        $schema: VEGA_LITE_SCHEMA,
        mark: 'bar',
      },
      metadata: {},
    };
    const { unmount } = render(<VegaChart spec={spec} onRender={onRender} />);
    await vi.waitFor(() => {
      expect(onRender).toHaveBeenCalledWith(mockView);
    });
    unmount();
    expect(onRender).toHaveBeenLastCalledWith(null);
  });

  it('calls onRender with null when vega_lite_spec is empty', async () => {
    const onRender = vi.fn();
    const spec: ChartSpec = {
      chart_type: 'bar',
      vega_lite_spec: {
        $schema: VEGA_LITE_SCHEMA,
        mark: 'bar',
      },
      metadata: {},
    };
    const { rerender } = render(<VegaChart spec={spec} onRender={onRender} />);
    await vi.waitFor(() => {
      expect(onRender).toHaveBeenCalledWith(mockView);
    });
    rerender(
      <VegaChart
        spec={{ chart_type: 'bar', vega_lite_spec: {}, metadata: {} }}
        onRender={onRender}
      />,
    );
    expect(onRender).toHaveBeenLastCalledWith(null);
  });
});
