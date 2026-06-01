'use client';

import { Card } from '@/components/ui/card';
import { formatMetadataJson, hasMetadataContent } from '@seal/metadata-contract';
import { metadataBadges, type MetadataBadge } from '@seal/metadata-summary';
import type { ChatMetadata, ExecutionMetadata } from '@/lib/execution-metadata';
import { cn } from '@/lib/utils';

interface MetadataPanelProps {
  metadata?: ChatMetadata | ExecutionMetadata | null;
  title?: string;
  subtitle?: string;
}

const BADGE_STYLES: Record<MetadataBadge['variant'], string> = {
  default: 'bg-primary/10 text-primary',
  warning: 'bg-amber-500/15 text-amber-700 dark:text-amber-400',
  destructive: 'bg-destructive/15 text-destructive',
  muted: 'bg-muted text-muted-foreground',
};

export function MetadataPanel({
  metadata,
  title = 'Execution metadata',
  subtitle,
}: MetadataPanelProps) {
  if (!hasMetadataContent(metadata ?? undefined)) {
    return null;
  }

  const badges = metadataBadges(metadata!);

  return (
    <Card className="console-panel space-y-3 p-4">
      <div>
        <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">{title}</p>
        {subtitle && <p className="text-muted-foreground mt-1 text-xs">{subtitle}</p>}
      </div>
      {badges.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {badges.map((badge) => (
            <span
              key={badge.label}
              className={cn(
                'rounded-md px-2 py-0.5 font-mono text-[11px] font-medium',
                BADGE_STYLES[badge.variant],
              )}
            >
              {badge.label}
            </span>
          ))}
        </div>
      )}
      <pre className="border-border bg-muted/30 max-h-64 overflow-auto rounded-md border p-3 font-mono text-xs">
        {formatMetadataJson(metadata)}
      </pre>
    </Card>
  );
}
