'use client';

import { useMemo, useState } from 'react';
import type { CatalogMatchItem, ChatMetadata } from '@seal/metadata-contract';
import { formatMetadataJson, hasMetadataContent } from '@seal/metadata-contract';
import { metadataBadges, type MetadataBadge } from '@seal/metadata-summary';
import type { TrustSurfaceInput } from '@seal/trust-explainability';
import {
  CheckCircle2Icon,
  CodeIcon,
  DatabaseIcon,
  LayersIcon,
  ListTreeIcon,
  SearchIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
  WrenchIcon,
  XCircleIcon,
} from 'lucide-react';

type TrustTab = 'sql' | 'sources' | 'provenance' | 'scope' | 'metadata';

const BADGE_STYLES: Record<MetadataBadge['variant'], string> = {
  default: 'bg-emerald-500/12 text-emerald-800 dark:text-emerald-300',
  warning: 'bg-amber-500/15 text-amber-800 dark:text-amber-300',
  destructive: 'bg-red-500/12 text-red-700 dark:text-red-300',
  muted: 'bg-muted text-muted-foreground',
};

const TAB_ICONS: Record<TrustTab, React.ReactNode> = {
  sql: <CodeIcon className="size-3" />,
  sources: <DatabaseIcon className="size-3" />,
  provenance: <ListTreeIcon className="size-3" />,
  scope: <ShieldCheckIcon className="size-3" />,
  metadata: <LayersIcon className="size-3" />,
};

const TAB_LABELS: Record<TrustTab, string> = {
  sql: 'SQL',
  sources: 'Sources',
  provenance: 'Provenance',
  scope: 'Scope',
  metadata: 'Metadata',
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
      return Boolean(
        meta?.tables_used?.length || meta?.columns_used?.length || meta?.catalog_matches?.length,
      );
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

function ScopeVerdict({
  inScope,
  source,
  reason,
}: {
  inScope: boolean;
  source: string;
  reason?: string | null;
}) {
  return (
    <div
      className={`flex items-start gap-3 rounded-lg border px-4 py-3 ${
        inScope
          ? 'border-emerald-500/25 bg-emerald-500/6 dark:border-emerald-500/20 dark:bg-emerald-500/8'
          : 'border-red-500/25 bg-red-500/6 dark:border-red-500/20 dark:bg-red-500/8'
      }`}
    >
      {inScope ? (
        <CheckCircle2Icon className="mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
      ) : (
        <XCircleIcon className="mt-0.5 size-4 shrink-0 text-red-600 dark:text-red-400" />
      )}
      <div className="space-y-1">
        <p className="text-sm font-medium">
          {inScope ? 'Query is in scope' : 'Query is out of scope'}
        </p>
        <p className="text-muted-foreground text-xs">
          Determined by <span className="font-mono font-medium">{source}</span> guardrail
          {reason ? <> — {reason}</> : null}
        </p>
      </div>
    </div>
  );
}

function RepairAttempts({ count }: { count: number }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-amber-500/25 bg-amber-500/6 px-4 py-3 dark:border-amber-500/20 dark:bg-amber-500/8">
      <WrenchIcon className="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400" />
      <div className="space-y-1">
        <p className="text-sm font-medium">
          {count} SQL repair {count === 1 ? 'attempt' : 'attempts'}
        </p>
        <p className="text-muted-foreground text-xs">
          The planner retried SQL generation to fix validation errors before producing the final
          query.
        </p>
      </div>
    </div>
  );
}

function CatalogMatchCard({ match }: { match: CatalogMatchItem }) {
  return (
    <div className="border-border/40 bg-muted/10 flex items-start gap-3 rounded-lg border px-4 py-3">
      <SearchIcon className="text-primary/70 mt-0.5 size-3.5 shrink-0" />
      <div className="min-w-0 space-y-0.5">
        <p className="truncate font-mono text-xs font-semibold">{catalogLabel(match)}</p>
        {match.description ? (
          <p className="text-muted-foreground text-xs leading-relaxed">{match.description}</p>
        ) : (
          <p className="text-muted-foreground/60 text-xs italic">No description in catalog</p>
        )}
      </div>
    </div>
  );
}

export function TrustPanel({
  sql,
  sources,
  metadata,
  className = '',
  title = 'Trust & explainability',
  subtitle = 'SQL, catalog provenance, scope, and execution metadata from the API.',
}: TrustPanelProps) {
  const input = useMemo(
    () => ({ sql, sources: sources ?? undefined, metadata }),
    [sql, sources, metadata],
  );
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
            <p className="text-foreground text-xs font-semibold tracking-[0.2em] uppercase">
              {title}
            </p>
            <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[10px] font-medium tracking-wide text-emerald-700 uppercase dark:text-emerald-300">
              verified
            </span>
          </div>
          {subtitle ? (
            <p className="text-muted-foreground max-w-prose text-xs">{subtitle}</p>
          ) : null}
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
        <div
          className="border-border/60 flex flex-wrap gap-0.5 border-b pb-0.5"
          role="tablist"
          aria-label="Trust panel sections"
        >
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
                  ? 'border-primary text-foreground -mb-px flex cursor-pointer items-center gap-1.5 border-b-2 px-3 py-1.5 font-mono text-[11px] font-medium tracking-wide uppercase'
                  : 'text-muted-foreground hover:text-foreground -mb-px flex cursor-pointer items-center gap-1.5 px-3 py-1.5 font-mono text-[11px] tracking-wide uppercase transition-colors'
              }
            >
              {TAB_ICONS[id]}
              {TAB_LABELS[id]}
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
        {/* ─── SQL ─── */}
        {activeTab === 'sql' && typeof sql === 'string' ? (
          <div className="space-y-2">
            <p className="text-muted-foreground text-[11px] font-medium tracking-wider uppercase">
              Generated SQL query
            </p>
            <pre className="border-border/50 bg-muted/25 max-h-72 overflow-auto rounded-lg border p-3.5 font-mono text-xs leading-relaxed">
              {sql}
            </pre>
          </div>
        ) : null}

        {/* ─── Sources ─── */}
        {activeTab === 'sources' && sources && sources.length > 0 ? (
          <div className="space-y-2">
            <p className="text-muted-foreground text-[11px] font-medium tracking-wider uppercase">
              Tables referenced ({sources.length})
            </p>
            <ul className="space-y-1.5">
              {sources.map((source) => (
                <li
                  key={source}
                  className="border-border/40 bg-muted/15 flex items-center gap-2.5 rounded-lg border px-3.5 py-2.5"
                >
                  <DatabaseIcon className="text-primary/60 size-3.5 shrink-0" />
                  <span className="font-mono text-xs font-medium">{source}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {/* ─── Provenance ─── */}
        {activeTab === 'provenance' && metadata ? (
          <div className="space-y-5">
            {metadata.catalog_matches && metadata.catalog_matches.length > 0 ? (
              <div className="space-y-2">
                <p className="text-muted-foreground text-[11px] font-medium tracking-wider uppercase">
                  Catalog matches ({metadata.catalog_matches.length})
                </p>
                <p className="text-muted-foreground/80 text-xs leading-relaxed">
                  Tables and columns matched from your data catalog with descriptions used to guide
                  SQL generation.
                </p>
                <div className="space-y-1.5">
                  {metadata.catalog_matches.map((match) => (
                    <CatalogMatchCard key={catalogLabel(match)} match={match} />
                  ))}
                </div>
              </div>
            ) : null}
            {metadata.tables_used && metadata.tables_used.length > 0 ? (
              <div className="space-y-2">
                <p className="text-muted-foreground text-[11px] font-medium tracking-wider uppercase">
                  Tables in SQL ({metadata.tables_used.length})
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {metadata.tables_used.map((table) => (
                    <span
                      key={table}
                      className="bg-muted/40 inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 font-mono text-xs"
                    >
                      <DatabaseIcon className="text-muted-foreground size-3" />
                      {table}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
            {metadata.columns_used && metadata.columns_used.length > 0 ? (
              <div className="space-y-2">
                <p className="text-muted-foreground text-[11px] font-medium tracking-wider uppercase">
                  Columns referenced ({metadata.columns_used.length})
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {metadata.columns_used.map((column) => (
                    <span
                      key={column}
                      className="bg-muted/40 rounded-md px-2.5 py-1 font-mono text-xs"
                    >
                      {column}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        {/* ─── Scope ─── */}
        {activeTab === 'scope' && metadata ? (
          <div className="space-y-4">
            {chatMeta?.scope ? (
              <ScopeVerdict
                inScope={chatMeta.scope.in_scope}
                source={chatMeta.scope.source}
                reason={chatMeta.scope.reason}
              />
            ) : null}
            {typeof metadata.repair_attempts === 'number' && metadata.repair_attempts > 0 ? (
              <RepairAttempts count={metadata.repair_attempts} />
            ) : null}
            {typeof metadata.repair_attempts === 'number' && metadata.repair_attempts === 0 ? (
              <div className="flex items-start gap-3 rounded-lg border border-emerald-500/25 bg-emerald-500/6 px-4 py-3 dark:border-emerald-500/20 dark:bg-emerald-500/8">
                <CheckCircle2Icon className="mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                <div className="space-y-1">
                  <p className="text-sm font-medium">No repairs needed</p>
                  <p className="text-muted-foreground text-xs">
                    SQL passed validation on the first attempt.
                  </p>
                </div>
              </div>
            ) : null}
            {chatMeta?.refusal ? (
              <div className="flex items-start gap-3 rounded-lg border border-red-500/25 bg-red-500/6 px-4 py-3 dark:border-red-500/20 dark:bg-red-500/8">
                <ShieldAlertIcon className="mt-0.5 size-4 shrink-0 text-red-600 dark:text-red-400" />
                <div className="space-y-1">
                  <p className="text-sm font-medium">Query was refused</p>
                  <p className="text-muted-foreground text-xs">
                    Guardrails determined this query cannot be answered.
                  </p>
                </div>
              </div>
            ) : null}
            {chatMeta?.suggested_queries && chatMeta.suggested_queries.length > 0 ? (
              <div className="space-y-2">
                <p className="text-muted-foreground text-[11px] font-medium tracking-wider uppercase">
                  Suggested alternatives
                </p>
                <ul className="space-y-1.5">
                  {chatMeta.suggested_queries.map((q) => (
                    <li
                      key={q}
                      className="border-border/40 bg-muted/10 rounded-lg border px-3.5 py-2.5 text-xs leading-relaxed"
                    >
                      {q}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {metadata.enhancement ? (
              <div className="space-y-2">
                <p className="text-muted-foreground text-[11px] font-medium tracking-wider uppercase">
                  Enhancement pipeline
                </p>
                <div className="border-border/40 space-y-2 rounded-lg border px-4 py-3">
                  <div className="flex items-center gap-2">
                    {metadata.enhancement.enabled ? (
                      <CheckCircle2Icon className="size-3.5 text-emerald-600 dark:text-emerald-400" />
                    ) : (
                      <XCircleIcon className="text-muted-foreground size-3.5" />
                    )}
                    <span className="text-xs font-medium">
                      Enhancement {metadata.enhancement.enabled ? 'enabled' : 'disabled'}
                    </span>
                  </div>
                  {metadata.enhancement.applied.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5 pl-5.5">
                      {metadata.enhancement.applied.map((step) => (
                        <span
                          key={step}
                          className="bg-primary/10 text-primary rounded-md px-2 py-0.5 font-mono text-[10px] font-medium"
                        >
                          {step}
                        </span>
                      ))}
                    </div>
                  ) : null}
                  {metadata.enhancement.vector_skipped_reason ? (
                    <p className="text-muted-foreground pl-5.5 text-xs">
                      Vector RAG skipped:{' '}
                      {metadata.enhancement.vector_skipped_reason.replace(/_/g, ' ')}
                    </p>
                  ) : null}
                  {metadata.enhancement.unavailable_reason ? (
                    <p className="text-muted-foreground pl-5.5 text-xs">
                      Unavailable: {metadata.enhancement.unavailable_reason.replace(/_/g, ' ')}
                    </p>
                  ) : null}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        {/* ─── Metadata (raw JSON) ─── */}
        {activeTab === 'metadata' && metadata ? (
          <div className="space-y-3">
            <div className="space-y-1">
              <p className="text-muted-foreground text-[11px] font-medium tracking-wider uppercase">
                Raw execution metadata
              </p>
              <p className="text-muted-foreground/80 text-xs">
                Full JSON payload returned from the API for this execution.
              </p>
            </div>
            {metadata.execution_time_ms != null || metadata.row_count != null ? (
              <div className="flex flex-wrap gap-3">
                {metadata.execution_time_ms != null ? (
                  <div className="border-border/40 bg-muted/15 rounded-lg border px-3.5 py-2">
                    <p className="text-muted-foreground text-[10px] font-medium tracking-wider uppercase">
                      Execution time
                    </p>
                    <p className="font-mono text-sm font-semibold">
                      {metadata.execution_time_ms.toFixed(0)}
                      <span className="text-muted-foreground ml-0.5 text-[10px] font-normal">
                        ms
                      </span>
                    </p>
                  </div>
                ) : null}
                {metadata.row_count != null ? (
                  <div className="border-border/40 bg-muted/15 rounded-lg border px-3.5 py-2">
                    <p className="text-muted-foreground text-[10px] font-medium tracking-wider uppercase">
                      Rows returned
                    </p>
                    <p className="font-mono text-sm font-semibold">
                      {metadata.row_count.toLocaleString()}
                      {metadata.truncated ? (
                        <span className="ml-1.5 text-[10px] font-normal text-amber-600 dark:text-amber-400">
                          (truncated)
                        </span>
                      ) : null}
                    </p>
                  </div>
                ) : null}
              </div>
            ) : null}
            {metadata.warnings && metadata.warnings.length > 0 ? (
              <div className="space-y-1.5">
                <p className="text-muted-foreground text-[11px] font-medium tracking-wider uppercase">
                  Warnings
                </p>
                {metadata.warnings.map((w) => (
                  <p
                    key={w}
                    className="rounded-md border border-amber-500/25 bg-amber-500/6 px-3 py-2 text-xs text-amber-800 dark:text-amber-300"
                  >
                    {w}
                  </p>
                ))}
              </div>
            ) : null}
            <pre className="border-border/50 bg-muted/25 max-h-72 overflow-auto rounded-lg border p-3 font-mono text-xs">
              {formatMetadataJson(metadata)}
            </pre>
          </div>
        ) : null}
      </div>
    </section>
  );
}
