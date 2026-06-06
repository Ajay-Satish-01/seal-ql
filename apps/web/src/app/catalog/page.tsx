'use client';

import { DatabaseScopeBanner } from '@/components/dashboard/database-scope-banner';
import { PageShell } from '@/components/dashboard/page-shell';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useConnection } from '@/hooks/use-connection';
import {
  catalogEntryKey,
  descriptionForEntry,
  descriptionLabelForEntry,
  patchPayloadForEntry,
  snapshotDescriptions,
  snapshotsEqual,
  withDescription,
} from '@/lib/catalog-descriptions';
import { docsPageUrl } from '@/lib/docs-url';
import {
  getCatalog,
  patchCatalogDescriptions,
  syncCatalog,
  type CatalogTable,
} from '@/lib/seal-api';
import { notifyErrorFrom, notifySuccess } from '@/lib/toast';
import { CheckCircle2, CircleAlert } from 'lucide-react';
import { useEffect, useMemo, useState, useTransition } from 'react';

const UNSAVED_DISCARD_MESSAGE =
  'You have unsaved description changes. Reload anyway and discard them?';

export default function CatalogPage() {
  const { apiUrl, apiKey } = useConnection();
  const [tables, setTables] = useState<CatalogTable[]>([]);
  const [savedSnapshot, setSavedSnapshot] = useState<Record<string, string>>({});
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const [syncPreserved, setSyncPreserved] = useState<number | null>(null);
  const [showCurationHelp, setShowCurationHelp] = useState(false);
  const [isPending, startTransition] = useTransition();
  const [isSaving, startSaveTransition] = useTransition();
  const [isSyncing, startSyncTransition] = useTransition();

  const currentSnapshot = useMemo(() => snapshotDescriptions(tables), [tables]);
  const hasUnsavedChanges = useMemo(
    () => tables.length > 0 && !snapshotsEqual(currentSnapshot, savedSnapshot),
    [tables.length, currentSnapshot, savedSnapshot],
  );
  const activeOverrideCount = useMemo(
    () => Object.values(savedSnapshot).filter((d) => d.trim().length > 0).length,
    [savedSnapshot],
  );
  const dirtyCount = useMemo(
    () =>
      tables.filter((table) => {
        const key = catalogEntryKey(table);
        return descriptionForEntry(table) !== (savedSnapshot[key] ?? '');
      }).length,
    [tables, savedSnapshot],
  );

  function applyLoadedTables(next: CatalogTable[]) {
    setTables(next);
    setSavedSnapshot(snapshotDescriptions(next));
  }

  function confirmDiscardUnsaved(): boolean {
    if (!hasUnsavedChanges) return true;
    return window.confirm(UNSAVED_DISCARD_MESSAGE);
  }

  function load(options?: { silent?: boolean; force?: boolean }) {
    if (!options?.force && !confirmDiscardUnsaved()) return;

    startTransition(async () => {
      try {
        const res = await getCatalog(apiUrl, apiKey.trim());
        applyLoadedTables(res.tables);
        if (!options?.silent) {
          notifySuccess(`Loaded ${res.tables.length} table(s)`);
        }
      } catch (e) {
        notifyErrorFrom(e, 'Failed to load catalog');
      }
    });
  }

  useEffect(() => {
    load({ silent: true, force: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiUrl, apiKey]);

  function updateDescription(key: string, value: string) {
    setTables((prev) =>
      prev.map((row) =>
        catalogEntryKey(row) === key ? withDescription(row, value) : row,
      ),
    );
  }

  function syncFromDb() {
    if (!confirmDiscardUnsaved()) return;

    startSyncTransition(async () => {
      try {
        const res = await syncCatalog(apiUrl, apiKey);
        setSyncPreserved(res.preserved);
        notifySuccess(
          `Catalog synced (+${res.added} ~${res.updated} preserved ${res.preserved}) — description overrides remain active`,
        );
        load({ silent: true, force: true });
      } catch (e) {
        notifyErrorFrom(e, 'Sync failed');
      }
    });
  }

  function save() {
    if (isPending || isSyncing) return;

    const dirtyTables = tables.filter((table) => {
      const key = catalogEntryKey(table);
      return descriptionForEntry(table) !== (savedSnapshot[key] ?? '');
    });
    if (dirtyTables.length === 0) return;

    startSaveTransition(async () => {
      try {
        const res = await patchCatalogDescriptions(
          apiUrl,
          apiKey,
          dirtyTables.map((table) =>
            patchPayloadForEntry(table, descriptionForEntry(table)),
          ),
        );
        applyLoadedTables(res.tables);
        setLastSavedAt(new Date());
        notifySuccess('Descriptions saved — active for the next query or chat turn');
      } catch (e) {
        notifyErrorFrom(e, 'Save failed');
      }
    });
  }

  const statusTone = hasUnsavedChanges
    ? 'border-amber-500/30 bg-amber-500/6 dark:border-amber-500/25 dark:bg-amber-500/8'
    : lastSavedAt
      ? 'border-emerald-500/30 bg-emerald-500/6 dark:border-emerald-500/25 dark:bg-emerald-500/8'
      : 'border-border/60 bg-muted/30';

  return (
    <PageShell
      title="Catalog"
      description="Edit table and view descriptions — saved overrides feed the planner on the next query or chat request."
      actions={
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => load()}
            disabled={isPending || isSaving || isSyncing}
          >
            {isPending ? 'Refreshing…' : 'Refresh'}
          </Button>
          <Button
            variant="outline"
            onClick={syncFromDb}
            disabled={isSyncing || isSaving || isPending}
          >
            {isSyncing ? 'Syncing…' : 'Sync from DB'}
          </Button>
        </div>
      }
    >
      <DatabaseScopeBanner feature="Catalog sync and YAML" />

      <div className={`console-panel flex flex-wrap items-start gap-3 rounded-lg border p-4 ${statusTone}`}>
        <div className="mt-0.5 shrink-0">
          {hasUnsavedChanges ? (
            <CircleAlert className="size-5 text-amber-700 dark:text-amber-300" />
          ) : lastSavedAt ? (
            <CheckCircle2 className="size-5 text-emerald-700 dark:text-emerald-300" />
          ) : (
            <CheckCircle2 className="text-muted-foreground size-5" />
          )}
        </div>
        <div className="min-w-0 flex-1 space-y-2 text-sm leading-relaxed">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-medium">
              {hasUnsavedChanges
                ? `${dirtyCount} unsaved change${dirtyCount === 1 ? '' : 's'}`
                : lastSavedAt
                  ? 'Descriptions active for planning'
                  : 'Catalog loaded'}
            </p>
            {hasUnsavedChanges && <Badge variant="outline">Unsaved</Badge>}
            {!hasUnsavedChanges && activeOverrideCount > 0 && (
              <Badge variant="secondary">{activeOverrideCount} active override(s)</Badge>
            )}
            {syncPreserved !== null && syncPreserved > 0 && !hasUnsavedChanges && (
              <Badge variant="secondary">Sync preserved {syncPreserved}</Badge>
            )}
          </div>
          <p className="text-muted-foreground">
            {hasUnsavedChanges
              ? 'Save to apply overrides before your next query or chat turn.'
              : lastSavedAt
                ? `Last saved at ${lastSavedAt.toLocaleTimeString()}. Overrides merge into the live catalog registry immediately.`
                : 'Saved descriptions are used on the next query or chat request — no API restart.'}
          </p>
          <button
            type="button"
            onClick={() => setShowCurationHelp((open) => !open)}
            className="text-primary text-xs hover:underline disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSaving || isSyncing || isPending}
          >
            {showCurationHelp ? 'Hide curation loop' : 'How the curation loop works'}
          </button>
          {showCurationHelp && (
            <p className="text-muted-foreground border-border/50 border-t pt-2 text-xs">
              Edits persist in workspace Postgres.{' '}
              <code className="font-mono">Sync from DB</code> rebuilds YAML; overrides are
              re-applied.{' '}
              <a
                href={docsPageUrl('/docs/data-catalog')}
                target="_blank"
                rel="noreferrer"
                className="text-primary hover:underline"
              >
                Data catalog docs
              </a>
            </p>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {tables.map((table) => {
          const key = catalogEntryKey(table);
          const savedDescription = savedSnapshot[key] ?? '';
          const currentDescription = descriptionForEntry(table);
          const isDirty = currentDescription !== savedDescription;
          const hasActiveOverride = savedDescription.trim().length > 0;
          const label = descriptionLabelForEntry(table);

          return (
            <Card key={key} className="console-panel space-y-2 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-mono text-sm font-medium">{key}</p>
                {table.kind && table.kind !== 'table' && (
                  <Badge variant="ghost" className="font-mono text-[10px] uppercase">
                    {table.kind.replace(/_/g, ' ')}
                  </Badge>
                )}
                {hasActiveOverride && !isDirty && (
                  <Badge variant="secondary">Active override</Badge>
                )}
                {isDirty && (
                  <Badge className="bg-amber-500/15 text-amber-900 dark:text-amber-200">
                    Unsaved
                  </Badge>
                )}
              </div>
              <label className="text-muted-foreground text-xs font-medium">{label}</label>
              <textarea
                value={currentDescription}
                onChange={(e) => updateDescription(key, e.target.value)}
                rows={2}
                className="border-input bg-background w-full rounded-md border px-3 py-2 text-sm"
                placeholder={`${label} override`}
                disabled={isSaving || isSyncing || isPending}
              />
            </Card>
          );
        })}
        {tables.length === 0 && !isPending && (
          <p className="text-muted-foreground text-sm">No tables loaded.</p>
        )}
      </div>

      {tables.length > 0 && (
        <div className="flex flex-wrap items-center gap-3">
          <Button
            onClick={save}
            disabled={isSaving || isPending || isSyncing || !hasUnsavedChanges}
          >
            {isSaving ? 'Saving…' : `Save ${dirtyCount > 0 ? dirtyCount : ''} description${dirtyCount === 1 ? '' : 's'}`.trim()}
          </Button>
        </div>
      )}
    </PageShell>
  );
}
