import React, { useEffect, useRef } from 'react';
import type { ChartSpec } from './types.js';

// Determine if we are in a browser environment
const isBrowser = typeof window !== 'undefined';

export interface VegaChartProps {
  /**
   * The chart spec returned by the Seal API.
   * If this is null or not provided, the component renders nothing.
   */
  spec: ChartSpec | null | undefined;
  /** Optional CSS class name for the container wrapper. */
  className?: string;
  /** Optional CSS inline styles for the container wrapper. */
  style?: React.CSSProperties;
  /** Enable or disable the Vega actions toolbar (export, view source, etc.). Defaults to false. */
  actions?: boolean;
  /** Explicitly set the width. If not provided, it relies on CSS/container sizing. */
  width?: number | string;
  /** Explicitly set the height. If not provided, it relies on CSS/container sizing. */
  height?: number | string;
  /** Enable dark mode styling. Defaults to false. */
  theme?: 'light' | 'dark';
  /** Called when the chart has successfully rendered. */
  onRender?: (view: unknown) => void;
  /** Called if an error occurs during rendering. */
  onError?: (error: Error) => void;
}

/**
 * A React component that renders Vega-Lite specifications returned by
 * the Seal API.
 *
 * Note: Requires `react` and `vega-embed` to be installed as peer dependencies.
 */
export const VegaChart: React.FC<VegaChartProps> = ({
  spec,
  className = '',
  style = {},
  actions = false,
  width,
  height,
  theme = 'light',
  onRender,
  onError,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<{ finalize: () => void } | null>(null);

  useEffect(() => {
    // If no spec, or it's a table/metric card, don't render vega
    if (!spec || !spec.vega_lite_spec || Object.keys(spec.vega_lite_spec).length === 0) {
      if (viewRef.current) {
        viewRef.current.finalize();
        viewRef.current = null;
      }
      return;
    }

    if (!containerRef.current || !isBrowser) return;

    let mounted = true;

    // Dynamically import vega-embed so it doesn't break SSR
    import('vega-embed')
      .then((vegaEmbed) => {
        if (!mounted) return;

        const embedOptions: Record<string, unknown> = {
          actions,
          theme: theme === 'dark' ? 'dark' : undefined,
        };

        // Inject width/height to the spec if provided
        const finalSpec = { ...spec.vega_lite_spec };
        if (width !== undefined) finalSpec.width = width;
        if (height !== undefined) finalSpec.height = height;

        return vegaEmbed.default(containerRef.current!, finalSpec, embedOptions);
      })
      .then((result) => {
        if (!mounted) {
          if (result) result.view.finalize();
          return;
        }
        if (result) {
          viewRef.current = result.view;
          if (onRender) onRender(result.view);
        }
      })
      .catch((err) => {
        if (!mounted) return;
        console.error('Failed to embed Vega chart', err);
        if (onError) onError(err);
      });

    return () => {
      mounted = false;
      if (viewRef.current) {
        viewRef.current.finalize();
        viewRef.current = null;
      }
    };
  }, [spec, actions, width, height, theme, onRender, onError]);

  // If the API says it's a table or metric card, rendering it should be handled
  // by the application using native React components, not Vega.
  if (spec?.chart_type === 'table' || spec?.chart_type === 'metric_card') {
    return null;
  }

  // Provide a base style that ensures the container takes up space,
  // unless explicitly overridden by the consumer.
  const baseStyle: React.CSSProperties = {
    width: width ?? '100%',
    height: height ?? '100%',
    minHeight: height ? undefined : '300px',
    ...style,
  };

  return <div ref={containerRef} className={`seal-vega-chart ${className}`} style={baseStyle} />;
};
