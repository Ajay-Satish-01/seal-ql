'use client';

import { ChartPanel } from '@/components/dashboard/chart-panel';
import { PageShell } from '@/components/dashboard/page-shell';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useConnection } from '@/hooks/use-connection';
import { postQuery } from '@/lib/seal-api';
import { notifyErrorFrom, notifyInfo, notifySuccess } from '@/lib/toast';
import type { ChartSpec } from 'seal';
import { useState, useTransition } from 'react';

export default function QueryPage() {
  const { apiUrl, apiKey, databaseId } = useConnection();
  const [query, setQuery] = useState('How many orders per month?');
  const [sql, setSql] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, unknown>[]>([]);
  const [chart, setChart] = useState<ChartSpec | null>(null);
  const [resolvedDatabaseId, setResolvedDatabaseId] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function runQuery() {
    const text = query.trim();
    if (!text) {
      notifyInfo('Enter a query first');
      return;
    }
    startTransition(async () => {
      try {
        const res = await postQuery(apiUrl, text, apiKey.trim(), databaseId);
        setSql(res.sql);
        setResults(res.results);
        setChart(res.chart);
        const metaDb =
          typeof res.metadata?.database_id === 'string' ? res.metadata.database_id : databaseId;
        setResolvedDatabaseId(metaDb);
        notifySuccess(`Query returned ${res.results.length} row(s) on "${metaDb}"`);
      } catch (e) {
        notifyErrorFrom(e, 'Query failed');
      }
    });
  }

  return (
    <PageShell
      title="Query"
      description={`POST /v1/query — NL → SQL on database "${databaseId}".`}
    >
      <Card className="console-panel space-y-4 p-4">
        <label
          htmlFor="nl-query"
          className="text-muted-foreground text-xs font-medium tracking-wide uppercase"
        >
          Natural language
        </label>
        <textarea
          id="nl-query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={3}
          className="border-input bg-background w-full rounded-md border px-3 py-2 text-sm"
        />
        <Button onClick={runQuery} disabled={isPending || !query.trim()}>
          {isPending ? 'Running…' : 'Run query'}
        </Button>
      </Card>

      {resolvedDatabaseId && (
        <p className="text-muted-foreground font-mono text-xs">
          database_id: {resolvedDatabaseId}
        </p>
      )}

      {sql && (
        <Card className="console-panel p-4">
          <p className="text-muted-foreground mb-2 text-xs font-medium tracking-wide uppercase">
            SQL
          </p>
          <pre className="overflow-x-auto font-mono text-xs">{sql}</pre>
        </Card>
      )}

      {(results.length > 0 || chart) && (
        <Card className="console-panel p-4">
          <p className="text-muted-foreground mb-3 text-xs font-medium tracking-wide uppercase">
            Results
          </p>
          <ChartPanel chart={chart} results={results} />
        </Card>
      )}
    </PageShell>
  );
}
