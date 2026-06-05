'use client';

import {
  formatMetadataJson,
  hasMetadataContent,
  type ChatMetadata,
  type ExecutionMetadata,
} from '@/lib/execution-metadata';
import { metadataBadges, type MetadataBadge } from '@seal/metadata-summary';
import { cn } from '@/lib/utils';

interface MetadataPanelProps {
  metadata?: ChatMetadata | ExecutionMetadata | null;
  title?: string;
}

const BADGE_STYLES: Record<MetadataBadge['variant'], string> = {
  default: 'bg-primary/10 text-primary',
  warning: 'bg-amber-500/15 text-amber-700 dark:text-amber-400',
  destructive: 'bg-destructive/15 text-destructive',
  muted: 'bg-muted text-muted-foreground',
};

export function MetadataPanel({ metadata, title = 'Execution metadata' }: MetadataPanelProps) {
  if (!hasMetadataContent(metadata ?? undefined)) {
    return null;
  }

  const badges = metadataBadges(metadata!);

  return (
    <div className="border-border/50 bg-card/50 space-y-3 rounded-lg border p-4">
      <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">{title}</p>
      {badges.length > 0 ? (
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
      ) : null}
      <pre className="border-border/40 bg-muted/30 max-h-64 overflow-auto rounded-md border p-3 font-mono text-xs">
        {formatMetadataJson(metadata)}
      </pre>
    </div>
  );
}
