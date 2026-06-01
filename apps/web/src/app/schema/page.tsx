'use client';

import { DatabaseScopeBanner } from '@/components/dashboard/database-scope-banner';
import { PageShell } from '@/components/dashboard/page-shell';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useConnection } from '@/hooks/use-connection';
import { getSchema } from '@/lib/seal-api';
import { notifyErrorFrom, notifySuccess } from '@/lib/toast';
import { useState, useTransition } from 'react';

export default function SchemaPage() {
  const { apiUrl, apiKey, databaseId } = useConnection();
  const [tables, setTables] = useState<
    Array<{
      name: string;
      schema_name?: string;
      columns?: Array<{ name: string; type: string }>;
    }>
  >([]);
  const [isPending, startTransition] = useTransition();

  function load() {
    startTransition(async () => {
      try {
        const res = await getSchema(apiUrl, apiKey.trim(), databaseId);
        const list = (res.tables ?? []).map((t) => {
          const row = t as {
            name: string;
            schema_name?: string;
            schema?: string;
            columns?: Array<{ name: string; data_type?: string; type?: string }>;
          };
          return {
            name: row.name,
            schema_name: row.schema_name ?? row.schema,
            columns: row.columns?.map((c) => ({
              name: c.name,
              type: c.data_type ?? c.type ?? 'unknown',
            })),
          };
        });
        setTables(list);
        notifySuccess(`Loaded ${list.length} table(s) from "${databaseId}"`);
      } catch (e) {
        notifyErrorFrom(e, 'Failed to load schema');
      }
    });
  }

  return (
    <PageShell
      title="Schema"
      description={`GET /v1/schema?database_id=${databaseId} — live DDL introspection for the selected database.`}
    >
      <DatabaseScopeBanner feature="The data catalog" />

      <Card className="console-panel space-y-4 p-4">
        <Button onClick={load} disabled={isPending}>
          {isPending ? 'Loading…' : 'Load schema'}
        </Button>
      </Card>

      {tables.length > 0 && (
        <Card className="console-panel space-y-4 p-4">
          <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
            Tables ({tables.length})
          </p>
          <ul className="space-y-3">
            {tables.map((table) => (
              <li key={`${table.schema_name ?? 'public'}.${table.name}`} className="text-sm">
                <p className="font-mono font-medium">
                  {table.schema_name ? `${table.schema_name}.` : ''}
                  {table.name}
                </p>
                {table.columns && table.columns.length > 0 && (
                  <ul className="text-muted-foreground mt-1 ml-2 list-inside list-disc font-mono text-xs">
                    {table.columns.map((col) => (
                      <li key={col.name}>
                        {col.name}: {col.type}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </PageShell>
  );
}
