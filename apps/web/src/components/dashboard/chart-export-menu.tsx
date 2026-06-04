'use client';

import { Download } from 'lucide-react';
import { useCallback, type RefObject } from 'react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { type MetricSnapshot } from '@seal/chart-spec';
import {
  chartExportFilename,
  exportMetricCardImage,
  exportResultsCsv,
  exportVegaImage,
  type ChartImageFormat,
  type VegaChartView,
} from '@/lib/chart-export';
import { notifyErrorFrom, notifyInfo, notifySuccess } from '@/lib/toast';

const IMAGE_EXPORT_OPTIONS: readonly { format: ChartImageFormat; label: string }[] = [
  { format: 'png', label: 'PNG image' },
  { format: 'svg', label: 'SVG image' },
];

interface ChartExportMenuProps {
  chartType: string;
  results: Record<string, unknown>[];
  vegaViewRef: RefObject<VegaChartView | null>;
  canExportVegaImages: boolean;
  metricSnapshot?: MetricSnapshot | null;
}

export function ChartExportMenu({
  chartType,
  results,
  vegaViewRef,
  canExportVegaImages,
  metricSnapshot,
}: ChartExportMenuProps) {
  const hasResults = results.length > 0;
  const canExportMetricImages = metricSnapshot != null;

  const runExport = useCallback(
    async (
      task: () => void | Promise<void>,
      {
        errorMessage,
        successFilename,
        preconditionMessage,
      }: {
        errorMessage: string;
        successFilename?: string;
        preconditionMessage?: string;
      },
    ) => {
      if (preconditionMessage) {
        notifyInfo(preconditionMessage);
        return;
      }
      try {
        await task();
        if (successFilename) {
          notifySuccess(`Exported ${successFilename}`);
        }
      } catch (error) {
        notifyErrorFrom(error, errorMessage);
      }
    },
    [],
  );

  const exportCsv = useCallback(() => {
    const filename = chartExportFilename(chartType, 'csv');
    void runExport(() => exportResultsCsv(results, filename), {
      errorMessage: 'CSV export failed',
      successFilename: filename,
      preconditionMessage: hasResults ? undefined : 'No rows to export',
    });
  }, [chartType, hasResults, results, runExport]);

  const exportImage = useCallback(
    (format: ChartImageFormat) => {
      const filename = chartExportFilename(chartType, format);
      const formatLabel = format.toUpperCase();

      if (canExportVegaImages) {
        void runExport(
          async () => {
            const view = vegaViewRef.current;
            if (!view) {
              throw new Error('Chart view unavailable');
            }
            await exportVegaImage(view, format, filename);
          },
          {
            errorMessage: `${formatLabel} export failed`,
            successFilename: filename,
            preconditionMessage: vegaViewRef.current
              ? undefined
              : 'Chart is still rendering — try again in a moment',
          },
        );
        return;
      }

      if (!canExportMetricImages || !metricSnapshot) {
        notifyInfo('No metric value to export');
        return;
      }

      void runExport(
        () =>
          exportMetricCardImage(
            metricSnapshot.label,
            metricSnapshot.displayValue,
            format,
            filename,
          ),
        {
          errorMessage: `${formatLabel} export failed`,
          successFilename: filename,
        },
      );
    },
    [canExportMetricImages, canExportVegaImages, chartType, metricSnapshot, runExport, vegaViewRef],
  );

  const canExportImages = canExportVegaImages || canExportMetricImages;
  if (!hasResults && !canExportImages) {
    return null;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button variant="outline" size="sm" className="ml-auto">
            <Download />
            Export
          </Button>
        }
      />
      <DropdownMenuContent align="end">
        {canExportImages
          ? IMAGE_EXPORT_OPTIONS.map(({ format, label }) => (
              <DropdownMenuItem
                key={format}
                onClick={() => void exportImage(format)}
                className="cursor-pointer"
              >
                {label}
              </DropdownMenuItem>
            ))
          : null}
        {hasResults ? (
          <DropdownMenuItem onClick={exportCsv} className="cursor-pointer">
            CSV data
          </DropdownMenuItem>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
