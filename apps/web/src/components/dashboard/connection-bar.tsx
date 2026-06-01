'use client';

import { Button } from '@/components/ui/button';
import { useConnection } from '@/hooks/use-connection';
import { DEFAULT_API_URL, normalizeBaseUrl } from '@/lib/connection';
import { probeApiConnection } from '@/lib/seal-api';
import { notifyError, notifySuccess } from '@/lib/toast';
import { useEffect, useState, useTransition } from 'react';

export function ConnectionBar() {
  const {
    apiUrl,
    apiKey,
    databaseId,
    registeredDatabases,
    revision,
    setConnection,
    setDatabaseId,
    registerDatabases,
    refreshDatabases,
  } = useConnection();
  const [draftUrl, setDraftUrl] = useState(DEFAULT_API_URL);
  const [draftKey, setDraftKey] = useState('');
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    // Resync the editable draft when the active connection changes externally.
    /* eslint-disable react-hooks/set-state-in-effect */
    setDraftUrl(apiUrl);
    setDraftKey(apiKey);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [apiUrl, apiKey, revision]);

  useEffect(() => {
    if (revision > 0) {
      void refreshDatabases();
    }
  }, [revision, refreshDatabases]);

  function apply() {
    const url = draftUrl.trim();
    const key = draftKey.trim();
    if (!url) {
      notifyError('API URL is required');
      return;
    }

    startTransition(async () => {
      const result = await probeApiConnection(url, key);
      if (!result.ok) {
        notifyError(result.message);
        return;
      }

      setConnection(url, key);
      registerDatabases(result.databases);
      const host = normalizeBaseUrl(url);
      const dbCount = result.databases.length;
      const dbNote =
        dbCount > 1 ? ` · ${dbCount} database(s): ${result.databases.map((d) => d.database_id).join(', ')}` : '';
      notifySuccess(
        result.tableCount > 0
          ? `Connected to ${host} (${result.tableCount} catalog table(s))${dbNote}`
          : `Connected to ${host}${dbNote}`,
      );
    });
  }

  return (
    <div className="console-grid border-border bg-card/60 flex flex-wrap items-end gap-3 border-b px-4 py-3 backdrop-blur-sm">
      <div className="min-w-[220px] flex-1">
        <label
          htmlFor="api-url"
          className="text-muted-foreground mb-1 block text-xs font-medium tracking-wide uppercase"
        >
          API URL
        </label>
        <input
          id="api-url"
          type="url"
          value={draftUrl}
          onChange={(e) => setDraftUrl(e.target.value)}
          className="border-input bg-background focus:ring-primary/40 w-full rounded-md border px-3 py-2 font-mono text-sm focus:ring-2 focus:outline-none"
          placeholder="http://localhost:8000"
          disabled={isPending}
        />
      </div>
      <div className="min-w-[200px] flex-1">
        <label
          htmlFor="api-key"
          className="text-muted-foreground mb-1 block text-xs font-medium tracking-wide uppercase"
        >
          X-API-Key
        </label>
        <input
          id="api-key"
          type="password"
          value={draftKey}
          onChange={(e) => setDraftKey(e.target.value)}
          className="border-input bg-background focus:ring-primary/40 w-full rounded-md border px-3 py-2 font-mono text-sm focus:ring-2 focus:outline-none"
          placeholder="Optional if auth disabled"
          autoComplete="off"
          disabled={isPending}
        />
      </div>
      <div className="min-w-[160px] shrink-0">
        <label
          htmlFor="database-id"
          className="text-muted-foreground mb-1 block text-xs font-medium tracking-wide uppercase"
        >
          Database
        </label>
        <select
          id="database-id"
          value={databaseId}
          onChange={(e) => setDatabaseId(e.target.value)}
          className="border-input bg-background focus:ring-primary/40 w-full rounded-md border px-3 py-2 font-mono text-sm focus:ring-2 focus:outline-none"
          disabled={isPending}
          title="database_id sent on query, chat, and schema requests"
        >
          {registeredDatabases.map((db) => (
            <option key={db.database_id} value={db.database_id}>
              {db.database_id}
              {db.is_default ? ' (default)' : ''} · {db.dialect}
            </option>
          ))}
          {!registeredDatabases.some((d) => d.database_id === databaseId) && (
            <option value={databaseId}>{databaseId}</option>
          )}
        </select>
      </div>
      <Button type="button" onClick={apply} className="shrink-0" disabled={isPending}>
        {isPending ? 'Connecting…' : 'Connect'}
      </Button>
    </div>
  );
}
