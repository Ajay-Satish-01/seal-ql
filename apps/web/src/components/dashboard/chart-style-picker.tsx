'use client';

import {
  CHART_COLOR_SCHEMES,
  CHART_TEMPLATES,
  chartStyleFromMetadata,
  formatChartStyleLabel,
  isClientStylePreview,
  metadataHasStyle,
  type ChartColorSchemeId,
  type ChartStyleSelection,
  type ChartTemplateId,
} from '@seal/chart-styles';
import { isNonVegaChartType } from '@seal/chart-spec';
import { Check, Eye, LayoutTemplate, Palette } from 'lucide-react';
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface ChartStylePickerProps {
  chartType: string;
  style: ChartStyleSelection;
  metadata?: Record<string, unknown> | null;
  onStyleChange: (style: ChartStyleSelection) => void;
  persistAction?: string;
}

function TemplateGlyph({ template }: { template: ChartTemplateId }) {
  const barClass =
    template === 'bold'
      ? 'h-3.5 w-1 rounded-sm bg-current'
      : template === 'rounded'
        ? 'h-3 w-1 rounded-full bg-current'
        : template === 'minimal'
          ? 'h-2.5 w-1 rounded-[1px] bg-current opacity-50'
          : 'h-3 w-1 rounded-[2px] bg-current';

  return (
    <span className="text-muted-foreground flex h-5 w-7 items-end justify-center gap-0.5">
      <span className={cn(barClass, template === 'default' && 'opacity-70')} />
      <span className={cn(barClass, template === 'minimal' ? 'opacity-40' : 'opacity-85')} />
      <span className={cn(barClass, template === 'minimal' ? 'opacity-50' : 'opacity-100')} />
    </span>
  );
}

function SectionLabel({
  icon: Icon,
  children,
}: {
  icon: typeof LayoutTemplate;
  children: ReactNode;
}) {
  return (
    <div className="text-muted-foreground flex items-center gap-2 font-mono text-[10px] font-medium tracking-[0.14em] uppercase">
      <span className="bg-primary/10 text-primary flex size-5 items-center justify-center rounded-md border border-primary/15">
        <Icon className="size-3 shrink-0" aria-hidden />
      </span>
      {children}
    </div>
  );
}

function StyleStatusBadge({ isPreview }: { isPreview: boolean }) {
  if (isPreview) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 font-mono text-[10px] font-medium tracking-wide text-amber-800 uppercase motion-safe:animate-pulse dark:text-amber-200">
        <Eye className="size-3 shrink-0 opacity-80" aria-hidden />
        Preview
      </span>
    );
  }

  return (
    <span className="border-border/80 bg-muted/50 text-muted-foreground inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10px] font-medium tracking-wide uppercase">
      <Check className="text-primary size-3 shrink-0" aria-hidden />
      Saved
    </span>
  );
}

export function ChartStylePicker({
  chartType,
  style,
  metadata,
  onStyleChange,
  persistAction = 'Run again',
}: ChartStylePickerProps) {
  if (isNonVegaChartType(chartType)) {
    return null;
  }

  const isPreview = isClientStylePreview(style, metadata);
  const savedStyle =
    isPreview && metadata && metadataHasStyle(metadata)
      ? chartStyleFromMetadata(metadata)
      : null;
  const activeTemplate =
    CHART_TEMPLATES.find((entry) => entry.id === style.template) ?? CHART_TEMPLATES[0];
  const activeScheme =
    CHART_COLOR_SCHEMES.find((entry) => entry.id === style.color_scheme) ??
    CHART_COLOR_SCHEMES[0];

  return (
    <section
      className={cn(
        'border-border/70 bg-card/60 console-grid relative overflow-hidden rounded-xl border shadow-sm',
        'motion-safe:animate-in motion-safe:fade-in-0 motion-safe:slide-in-from-bottom-1 motion-safe:duration-300',
      )}
      aria-label="Chart appearance"
    >
      <div className="from-primary/8 via-primary/2 pointer-events-none absolute inset-0 bg-gradient-to-br to-transparent" />
      <div className="via-primary/60 from-primary/80 to-accent/60 pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r" />

      <div className="relative space-y-4 p-3.5 sm:p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <p className="font-heading text-foreground text-sm font-medium tracking-tight">
              Chart appearance
            </p>
            <p className="text-muted-foreground font-mono text-[11px] tabular-nums">
              {formatChartStyleLabel(style)}
            </p>
          </div>
          <StyleStatusBadge isPreview={isPreview} />
        </div>

        <div className="space-y-2.5">
          <SectionLabel icon={LayoutTemplate}>Template</SectionLabel>
          <div
            className="grid grid-cols-2 gap-1.5 sm:grid-cols-4"
            role="radiogroup"
            aria-label="Chart template"
          >
            {CHART_TEMPLATES.map((template, index) => {
              const selected = style.template === template.id;
              return (
                <button
                  key={template.id}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() =>
                    onStyleChange({
                      ...style,
                      template: template.id,
                    })
                  }
                  style={{ animationDelay: `${index * 40}ms` }}
                  className={cn(
                    'group relative flex flex-col items-center gap-1.5 rounded-lg border px-2 py-2.5 text-center transition-all',
                    'focus-visible:ring-primary focus-visible:ring-2 focus-visible:outline-none',
                    'motion-safe:animate-in motion-safe:fade-in-0 motion-safe:zoom-in-95 motion-safe:duration-200 motion-safe:[animation-fill-mode:backwards]',
                    selected
                      ? 'border-primary/50 bg-primary/8 ring-primary/25 ring-1'
                      : 'border-border/60 bg-background/70 hover:border-border hover:bg-muted/40',
                  )}
                >
                  {selected ? (
                    <span className="bg-primary text-primary-foreground absolute top-1.5 right-1.5 flex size-3.5 items-center justify-center rounded-full shadow-sm">
                      <Check className="size-2" strokeWidth={3} aria-hidden />
                    </span>
                  ) : null}
                  <TemplateGlyph template={template.id} />
                  <span
                    className={cn(
                      'text-[11px] leading-none font-medium',
                      selected ? 'text-foreground' : 'text-muted-foreground group-hover:text-foreground',
                    )}
                  >
                    {template.label}
                  </span>
                </button>
              );
            })}
          </div>
          <p className="text-muted-foreground border-border/40 border-l-2 pl-2.5 text-xs leading-relaxed">
            {activeTemplate.description}
          </p>
        </div>

        <div className="border-border/50 space-y-2.5 border-t pt-4">
          <SectionLabel icon={Palette}>Palette</SectionLabel>
          <div
            className="flex flex-wrap gap-2.5"
            role="radiogroup"
            aria-label="Chart color scheme"
          >
            {CHART_COLOR_SCHEMES.map((scheme, index) => {
              const selected = style.color_scheme === scheme.id;
              return (
                <button
                  key={scheme.id}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  aria-label={scheme.label}
                  title={scheme.label}
                  onClick={() =>
                    onStyleChange({
                      ...style,
                      color_scheme: scheme.id as ChartColorSchemeId,
                    })
                  }
                  style={{ animationDelay: `${index * 35}ms` }}
                  className={cn(
                    'group flex flex-col items-center gap-1.5 rounded-lg p-0.5 transition-all',
                    'focus-visible:ring-primary focus-visible:ring-2 focus-visible:outline-none',
                    'motion-safe:animate-in motion-safe:fade-in-0 motion-safe:zoom-in-95 motion-safe:duration-200 motion-safe:[animation-fill-mode:backwards]',
                    selected ? 'scale-100' : 'opacity-75 hover:scale-[1.03] hover:opacity-100',
                  )}
                >
                  <span
                    className={cn(
                      'relative flex h-9 w-9 items-center justify-center rounded-full border-2 p-0.5 shadow-sm transition-all',
                      selected
                        ? 'border-primary ring-primary/25 ring-2'
                        : 'border-border/50 group-hover:border-muted-foreground/35 group-hover:shadow-md',
                    )}
                  >
                    {selected ? (
                      <span className="bg-background text-primary absolute -top-0.5 -right-0.5 z-10 flex size-3.5 items-center justify-center rounded-full border border-primary/30 shadow-sm">
                        <Check className="size-2" strokeWidth={3} aria-hidden />
                      </span>
                    ) : null}
                    <span className="flex h-full w-full overflow-hidden rounded-full">
                      {scheme.swatches.slice(0, 5).map((color, swatchIndex) => (
                        <span
                          key={`${scheme.id}-${swatchIndex}`}
                          className="h-full flex-1"
                          style={{ backgroundColor: color }}
                        />
                      ))}
                    </span>
                  </span>
                  <span
                    className={cn(
                      'max-w-[4.75rem] truncate font-mono text-[9px] leading-none',
                      selected ? 'text-foreground font-medium' : 'text-muted-foreground',
                    )}
                  >
                    {scheme.label}
                  </span>
                </button>
              );
            })}
          </div>
          <p className="text-muted-foreground font-mono text-[11px]">
            Active palette:{' '}
            <span className="text-foreground inline-flex items-center gap-1.5">
              <span
                className="inline-flex h-2.5 w-6 overflow-hidden rounded-full border border-border/60"
                aria-hidden
              >
                {activeScheme.swatches.slice(0, 5).map((color, index) => (
                  <span
                    key={`active-${index}`}
                    className="h-full flex-1"
                    style={{ backgroundColor: color }}
                  />
                ))}
              </span>
              {activeScheme.label}
            </span>
          </p>
        </div>

        {isPreview ? (
          <div
            className={cn(
              'flex gap-2.5 rounded-lg border border-amber-500/25 bg-amber-500/6 px-3 py-2.5 dark:bg-amber-500/8',
              'motion-safe:animate-in motion-safe:fade-in-0 motion-safe:slide-in-from-bottom-1 motion-safe:duration-300',
            )}
            role="status"
          >
            <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md border border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-200">
              <Eye className="size-3.5" aria-hidden />
            </span>
            <div className="space-y-1 text-xs leading-relaxed">
              <p className="font-medium text-amber-900 dark:text-amber-100">
                Showing a local preview
              </p>
              <p className="text-amber-900/80 dark:text-amber-100/80">
                The chart renders as{' '}
                <span className="font-medium text-amber-950 dark:text-amber-50">
                  {formatChartStyleLabel(style)}
                </span>
                {savedStyle ? (
                  <>
                    , but the API response still stores{' '}
                    <span className="font-medium text-amber-950 dark:text-amber-50">
                      {formatChartStyleLabel(savedStyle)}
                    </span>
                  </>
                ) : null}
                . {persistAction} to persist this style in{' '}
                <code className="rounded bg-amber-500/10 px-1 py-px font-mono text-[10px]">
                  chart.metadata
                </code>
                .
              </p>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
