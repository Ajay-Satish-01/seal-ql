'use client';

import { useMemo, useState } from 'react';
import type { CatalogMatchItem, ChatMetadata } from '@seal/metadata-contract';
import { formatMetadataJson, hasMetadataContent } from '@seal/metadata-contract';
import { metadataBadges, type MetadataBadge } from '@seal/metadata-summary';
import type { TrustSurfaceInput } from '@seal/trust-explainability';

type TrustTab = 'sql' | 'sources' | 'provenance' | 'scope' | 'metadata';

const BADGE_STYLES: Record<MetadataBadge['variant'], string> = {
  default: 'bg-emerald-500/12 text-emerald-800 dark:text-emerald-300',
  warning: 'bg-amber-500/15 text-amber-800 dark:text-amber-300',
  destructive: 'bg-red-500/12 text-red-700 dark:text-red-300',
  muted: 'bg-muted text-muted-foreground',
};

export interface TrustPanelProps extends Omit<TrustSurfaceInput, 'sources'> {
  sources?: readonly string[] | null;
  className?: string;
  title?: string;
  subtitle?: string;
}

function catalogLabel(match: CatalogMatchItem): string {
  return match.schema ? `${match.schema}.${match.name}` : match.name;
}

function tabHasContent(tab: TrustTab, input: TrustSurfaceInput): boolean {
  const meta = input.metadata;
  const chatMeta = meta as ChatMetadata | undefined;
  switch (tab) {
    case 'sql':
      return typeof input.sql === 'string' && input.sql.length > 0;
    case 'sources':
      return Boolean(input.sources && input.sources.length > 0);
    case 'provenance':
      return Boolean(meta?.tables_used?.length || meta?.columns_used?.length || meta?.catalog_matches?.length);
    case 'scope':
      return Boolean(
        chatMeta?.scope ||
          (typeof meta?.repair_attempts === 'number' && meta.repair_attempts > 0) ||
          chatMeta?.refusal ||
          (chatMeta?.suggested_queries && chatMeta.suggested_queries.length > 0),
      );
    case 'metadata':
      return hasMetadataContent(meta ?? undefined);
    default:
      return false;
  }
}

function defaultTab(input: TrustSurfaceInput): TrustTab {
  const order: TrustTab[] = ['sql', 'provenance', 'sources', 'scope', 'metadata'];
  for (const tab of order) {
    if (tabHasContent(tab, input)) return tab;
  }
  return 'metadata';
}

export function TrustPanel({
  sql,
  sources,
  metadata,
  className = '',
  title = 'Trust & explainability',
  subtitle = 'SQL, catalog provenance, scope, and execution metadata from the API.',
}: TrustPanelProps) {
  const input = useMemo(() => ({ sql, sources: sources ?? undefined, metadata }), [sql, sources, metadata]);
  const [tab, setTab] = useState<TrustTab>(() => defaultTab(input));

  const tabs = useMemo(
    () =>
      (['sql', 'sources', 'provenance', 'scope', 'metadata'] as const).filter((id) =>
        tabHasContent(id, input),
      ),
    [input],
  );

  const activeTab = tabs.includes(tab) ? tab : (tabs[0] ?? 'metadata');
  const badges = metadata ? metadataBadges(metadata) : [];
  const chatMeta = metadata as ChatMetadata | undefined;

  return (
    <section
      className={`border-border/80 bg-card/40 space-y-4 rounded-lg border p-4 backdrop-blur-sm ${className}`.trim()}
      aria-label={title}
    >
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-foreground text-xs font-semibold tracking-[0.2em] uppercase">{title}</p>
            <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[10px] font-medium tracking-wide text-emerald-700 uppercase dark:text-emerald-300">
              verified
            </span>
          </div>
          {subtitle ? <p className="text-muted-foreground max-w-prose text-xs">{subtitle}</p> : null}
        </div>
        {badges.length > 0 ? (
          <div className="flex max-w-full flex-wrap justify-end gap-1.5">
            {badges.map((badge) => (
              <span
                key={badge.label}
                className={`rounded-md px-2 py-0.5 font-mono text-[11px] font-medium ${BADGE_STYLES[badge.variant]}`}
              >
                {badge.label}
              </span>
            ))}
          </div>
        ) : null}
      </header>

      {tabs.length > 0 ? (
        <div className="border-border/60 flex flex-wrap gap-1 border-b pb-0.5" role="tablist" aria-label="Trust panel sections">
          {tabs.map((id) => (
            <button
              key={id}
              id={`tab-${id}`}
              type="button"
              role="tab"
              aria-selected={activeTab === id}
              aria-controls={`panel-${id}`}
              onClick={() => setTab(id)}
              className={
                activeTab === id
                  ? 'border-primary text-foreground -mb-px border-b-2 px-3 py-1.5 font-mono text-[11px] font-medium tracking-wide uppercase'
                  : 'text-muted-foreground hover:text-foreground px-3 py-1.5 font-mono text-[11px] tracking-wide uppercase transition-colors'
              }
            >
              {id}
            </button>
          ))}
        </div>
      ) : null}

      <div
        id={`panel-${activeTab}`}
        role="tabpanel"
        aria-labelledby={`tab-${activeTab}`}
        className="min-h-[4rem]"
      >
        {activeTab === 'sql' && typeof sql === 'string' ? (
          <pre className="border-border/50 bg-muted/25 max-h-72 overflow-auto rounded-md border p-3 font-mono text-xs leading-relaxed">
            {sql}
          </pre>
        ) : null}

        {activeTab === 'sources' && sources && sources.length > 0 ? (
          <ul className="space-y-2">
            {sources.map((source) => (
              <li
                key={source}
                className="border-border/40 bg-muted/20 flex items-center gap-2 rounded-md border px-3 py-2 font-mono text-xs"
              >
                <span className="bg-primary/15 text-primary rounded px-1.5 py-0.5 text-[10px] tracking-wider uppercase">
                  table
                </span>
                {source}
              </li>
            ))}
          </ul>
        ) : null}

        {activeTab === 'provenance' && metadata ? (
          <div className="space-y-4 text-sm">
            {metadata.tables_used && metadata.tables_used.length > 0 ? (
              <div>
                <p className="text-muted-foreground mb-2 text-[11px] font-medium tracking-wider uppercase">Tables in SQL</p>
                <div className="flex flex-wrap gap-1.5">
                  {metadata.tables_used.map((table) => (
                    <span key={table} className="bg-muted/40 rounded-md px-2 py-1 font-mono text-xs">
                      {table}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
            {metadata.columns_used && metadata.columns_used.length > 0 ? (
              <div>
                <p className="text-muted-foreground mb-2 text-[11px] font-medium tracking-wider uppercase">Columns referenced</p>
                <div className="flex flex-wrap gap-1.5">
                  {metadata.columns_used.map((column) => (
                    <span key={column} className="bg-muted/40 rounded-md px-2 py-1 font-mono text-xs">
                      {column}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
            {metadata.catalog_matches && metadata.catalog_matches.length > 0 ? (
              <div>
                <p className="text-muted-foreground mb-2 text-[11px] font-medium tracking-wider uppercase">Catalog matches</p>
                <ul className="space-y-2">
                  {metadata.catalog_matches.map((match) => (
                    <li key={catalogLabel(match)} className="border-border/40 rounded-md border px-3 py-2">
                      <p className="font-mono text-xs font-medium">{catalogLabel(match)}</p>
                      {match.description ? <p className="text-muted-foreground mt-1 text-xs leading-relaxed">{match.description}</p> : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}

        {activeTab === 'scope' && metadata ? (
          <div className="space-y-3 text-sm">
            {chatMeta?.scope ? (
              <div className="border-border/40 rounded-md border px-3 py-2">
                <p className="text-muted-foreground text-[11px] font-medium tracking-wider uppercase">Guardrails scope</p>
                <p className="mt-1 font-mono text-xs">
                  in_scope: {String(chatMeta.scope.in_scope)} · source: {chatMeta.scope.source}
                  {chatMeta.scope.reason ? ` · ${chatMeta.scope.reason}` : ''}
                </p>
              </div>
            ) : null}
            {typeof metadata.repair_attempts === 'number' ? (
              <p className="font-mono text-xs">
                repair_attempts: <span className="text-foreground">{metadata.repair_attempts}</span>
              </p>
            ) : null}
            {chatMeta?.refusal ? <p className="text-destructive font-mono text-xs">refusal: true</p> : null}
            {chatMeta?.suggested_queries && chatMeta.suggested_queries.length > 0 ? (
              <div>
                <p className="text-muted-foreground mb-2 text-[11px] font-medium tracking-wider uppercase">Suggested queries</p>
                <ul className="list-inside list-disc space-y-1 text-xs">
                  {chatMeta.suggested_queries.map((q) => (
                    <li key={q}>{q}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}

        {activeTab === 'metadata' && metadata ? (
          <pre className="border-border/50 bg-muted/25 max-h-72 overflow-auto rounded-md border p-3 font-mono text-xs">
            {formatMetadataJson(metadata)}
          </pre>
        ) : null}
      </div>
    </section>
  );
}
