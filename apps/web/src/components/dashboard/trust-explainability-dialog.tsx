'use client';

import { ChartPanel } from '@/components/dashboard/chart-panel';
import { TrustPanel } from '@/components/dashboard/trust-panel';
import { MetadataPanel } from '@/components/dashboard/metadata-panel';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogBody,
  DialogCloseButton,
  DialogDescription,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from '@/components/ui/dialog';
import type { ChatMetadata } from '@/lib/execution-metadata';
import { hasMetadataContent } from '@seal/metadata-contract';
import { shouldShowTrustPanel } from '@seal/trust-explainability';
import type { ChartSpec } from 'seal';
import { ShieldCheckIcon } from 'lucide-react';

export interface ExplainabilitySurface {
  sql?: string | null;
  sources?: readonly string[] | null;
  metadata?: ChatMetadata | null;
  chart?: ChartSpec | null;
  results?: readonly Record<string, unknown>[];
}

export interface TrustExplainabilityDialogProps extends ExplainabilitySurface {
  trustExplainabilityEnabled: boolean;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onOpenChangeComplete?: (open: boolean) => void;
}

export interface ExplainabilityTriggerProps {
  disabled?: boolean;
  className?: string;
  onClick: () => void;
}

function hasFallbackExplainabilityContent(
  sql: string | null | undefined,
  metadata: ChatMetadata | null | undefined,
): boolean {
  return Boolean(sql || hasMetadataContent(metadata ?? undefined));
}

export function shouldRenderExplainabilityTrigger(
  trustExplainabilityEnabled: boolean,
  surface: ExplainabilitySurface,
  alwaysShow = false,
): boolean {
  const trustInput = {
    sql: surface.sql,
    sources: surface.sources ?? undefined,
    metadata: surface.metadata,
  };
  const showTrustPanel =
    trustExplainabilityEnabled &&
    (shouldShowTrustPanel(trustExplainabilityEnabled, trustInput) || alwaysShow);
  const showFallback =
    !trustExplainabilityEnabled &&
    (alwaysShow || hasFallbackExplainabilityContent(surface.sql, surface.metadata));
  return showTrustPanel || showFallback;
}

export function ExplainabilityTrigger({
  disabled = false,
  className,
  onClick,
}: ExplainabilityTriggerProps) {
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      disabled={disabled}
      onClick={onClick}
      className={`hover:border-primary/35 hover:bg-primary/5 cursor-pointer gap-1.5 font-mono text-[11px] tracking-wide uppercase disabled:cursor-not-allowed ${className ?? ''}`.trim()}
    >
      <ShieldCheckIcon className="size-3.5" />
      Explainability
    </Button>
  );
}

export function TrustExplainabilityDialog({
  sql,
  sources,
  metadata,
  chart = null,
  results = [],
  trustExplainabilityEnabled,
  open,
  onOpenChange,
  onOpenChangeComplete,
}: TrustExplainabilityDialogProps) {
  const trustInput = { sql, sources: sources ?? undefined, metadata };
  const hasTrustContent = shouldShowTrustPanel(trustExplainabilityEnabled, trustInput);
  const showTrustPanel = trustExplainabilityEnabled && hasTrustContent;
  const hasResults = results.length > 0 || chart != null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange} onOpenChangeComplete={onOpenChangeComplete}>
      <DialogPopup finalFocus={false}>
        {showTrustPanel ? (
          <>
            <DialogTitle className="sr-only">Trust & explainability</DialogTitle>
            <DialogDescription className="sr-only">
              SQL, catalog provenance, guardrails scope, and execution metadata for this turn.
            </DialogDescription>
            <DialogCloseButton className="absolute top-3 right-3 z-10 cursor-pointer" />
            <DialogBody>
              <div className="space-y-5">
                <TrustPanel
                  sql={sql}
                  sources={sources}
                  metadata={metadata}
                  title="Trust & explainability"
                  subtitle="SQL, catalog provenance, guardrails scope, and execution metadata for this turn."
                  className="border-0 bg-transparent p-0 shadow-none backdrop-blur-none"
                />
                {hasResults ? (
                  <section className="border-border/60 space-y-3 border-t pt-4">
                    <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
                      Results
                    </p>
                    <ChartPanel chart={chart} results={[...results]} />
                  </section>
                ) : null}
              </div>
            </DialogBody>
          </>
        ) : (
          <>
            <DialogHeader>
              <div className="space-y-1 pr-8">
                <DialogTitle>Execution metadata</DialogTitle>
                <DialogDescription>Metadata from seal.meta for this chat turn.</DialogDescription>
              </div>
              <DialogCloseButton className="absolute top-4 right-4 cursor-pointer" />
            </DialogHeader>
            <DialogBody>
              <div className="space-y-4">
                {sql ? (
                  <div className="space-y-2">
                    <p className="text-muted-foreground text-[11px] font-medium tracking-wider uppercase">
                      SQL
                    </p>
                    <pre className="border-border/50 bg-muted/25 max-h-72 overflow-auto rounded-md border p-3 font-mono text-xs leading-relaxed">
                      {sql}
                    </pre>
                  </div>
                ) : null}
                <MetadataPanel
                  metadata={metadata}
                  title="Chat metadata"
                  subtitle="Flat seal.meta fields (JSON chat nests the same under metadata)."
                />
                {hasResults ? (
                  <section className="space-y-3">
                    <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
                      Results
                    </p>
                    <ChartPanel chart={chart} results={[...results]} />
                  </section>
                ) : null}
              </div>
            </DialogBody>
          </>
        )}
      </DialogPopup>
    </Dialog>
  );
}
