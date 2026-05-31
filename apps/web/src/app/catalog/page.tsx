'use client';

import { DatabaseScopeBanner } from '@/components/dashboard/database-scope-banner';
import { PageShell } from '@/components/dashboard/page-shell';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useConnection } from '@/hooks/use-connection';
import {
  getCatalog,
  patchCatalogDescriptions,
  syncCatalog,
  type CatalogTable,
} from '@/lib/seal-api';
import { notifyErrorFrom, notifySuccess } from '@/lib/toast';
import { useEffect, useState, useTransition } from 'react';

export default function CatalogPage() {
  const { apiUrl, apiKey } = useConnection();
  const [tables, setTables] = useState<CatalogTable[]>([]);
  const [isPending, startTransition] = useTransition();
  const [isSaving, startSaveTransition] = useTransition();
  const [isSyncing, startSyncTransition] = useTransition();

  function load(options?: { silent?: boolean }) {
    startTransition(async () => {
      try {
        const res = await getCatalog(apiUrl, apiKey.trim());
        setTables(res.tables);
        if (!options?.silent) {
          notifySuccess(`Loaded ${res.tables.length} table(s)`);
        }
      } catch (e) {
        notifyErrorFrom(e, 'Failed to load catalog');
      }
    });
  }

  useEffect(() => {
    load({ silent: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiUrl, apiKey]);

  function updateDescription(index: number, value: string) {
    setTables((prev) => {
      const next = [...prev];
      const row = { ...next[index] };
      row.table_description = value;
      next[index] = row;
      return next;
    });
  }

  function syncFromDb() {
    startSyncTransition(async () => {
      try {
        const res = await syncCatalog(apiUrl, apiKey);
        notifySuccess(`Catalog synced (+${res.added} ~${res.updated} preserved ${res.preserved})`);
        load({ silent: true });
      } catch (e) {
        notifyErrorFrom(e, 'Sync failed');
      }
    });
  }

  function save() {
    startSaveTransition(async () => {
      try {
        const res = await patchCatalogDescriptions(
          apiUrl,
          apiKey,
          tables.map((t) => ({
            name: t.name,
            schema: t.schema ?? 'public',
            table_description: t.table_description ?? '',
          })),
        );
        setTables(res.tables);
        notifySuccess('Catalog descriptions saved');
      } catch (e) {
        notifyErrorFrom(e, 'Save failed');
      }
    });
  }

  return (
    <PageShell
      title="Catalog"
      description="GET /v1/catalog, PATCH descriptions (Postgres), Sync from DB — YAML regenerates; DB overrides win."
      actions={
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => load()} disabled={isPending}>
            {isPending ? 'Refreshing…' : 'Refresh'}
          </Button>
          <Button variant="outline" onClick={syncFromDb} disabled={isSyncing}>
            {isSyncing ? 'Syncing…' : 'Sync from DB'}
          </Button>
        </div>
      }
    >
      <DatabaseScopeBanner feature="Catalog sync and YAML" />
      <div className="space-y-3">
        {tables.map((table, i) => (
          <Card
            key={`${table.schema ?? 'public'}.${table.name}`}
            className="console-panel space-y-2 p-4"
          >
            <p className="font-mono text-sm font-medium">
              {table.schema ?? 'public'}.{table.name}
            </p>
            <textarea
              value={table.table_description ?? ''}
              onChange={(e) => updateDescription(i, e.target.value)}
              rows={2}
              className="border-input bg-background w-full rounded-md border px-3 py-2 text-sm"
              placeholder="Table description override"
            />
          </Card>
        ))}
        {tables.length === 0 && !isPending && (
          <p className="text-muted-foreground text-sm">No tables loaded.</p>
        )}
      </div>

      {tables.length > 0 && (
        <Button onClick={save} disabled={isSaving}>
          {isSaving ? 'Saving…' : 'Save descriptions'}
        </Button>
      )}
    </PageShell>
  );
}
