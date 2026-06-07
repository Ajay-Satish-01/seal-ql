'use client';

import { ChartPanel } from '@/components/dashboard/chart-panel';
import { MetadataPanel } from '@/components/dashboard/metadata-panel';
import { ReasoningPanel } from '@/components/dashboard/reasoning-panel';
import { shouldShowTrustPanel } from '@seal/trust-explainability';
import { TrustPanel } from '@/components/dashboard/trust-panel';
import { PageShell } from '@/components/dashboard/page-shell';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useConnection } from '@/hooks/use-connection';
import type { QueryMetadata } from '@/lib/execution-metadata';
import { postQuery } from '@/lib/seal-api';
import { notifyErrorFrom, notifyInfo, notifySuccess } from '@/lib/toast';
import type { ChartSpec } from 'seal';
import { useState, useTransition } from 'react';

export default function QueryPage() {
  const { apiUrl, apiKey, databaseId, trustExplainabilityEnabled } = useConnection();
  const [query, setQuery] = useState('How many orders per month?');
  const [sql, setSql] = useState<string | null>(null);
  const [sources, setSources] = useState<string[]>([]);
  const [results, setResults] = useState<Record<string, unknown>[]>([]);
  const [chart, setChart] = useState<ChartSpec | null>(null);
  const [metadata, setMetadata] = useState<QueryMetadata | null>(null);
  const [assistantMessage, setAssistantMessage] = useState<string | null>(null);
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
        setSql(res.sql || null);
        setSources(res.sources ?? []);
        setResults(res.results);
        setChart(res.chart);
        setMetadata(res.metadata ?? null);
        setAssistantMessage(res.message ?? null);
        const metaDb =
          typeof res.metadata?.database_id === 'string' ? res.metadata.database_id : databaseId;
        if (res.metadata?.reasoning?.clarification_required) {
          notifyInfo('More detail needed — see clarifying questions below');
        } else {
          notifySuccess(`Query returned ${res.results.length} row(s) on "${metaDb}"`);
        }
      } catch (e) {
        notifyErrorFrom(e, 'Query failed');
      }
    });
  }

  const showTrustPanel = shouldShowTrustPanel(trustExplainabilityEnabled, {
    sql,
    sources,
    metadata,
  });

  const hasResults = results.length > 0 || chart != null;
  const hasAssistantMessage = Boolean(assistantMessage?.trim());

  return (
    <PageShell
      title="Query"
      description={`POST /v1/query — NL → SQL on database "${databaseId}". Execution metadata is returned under metadata.`}
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

      {metadata?.reasoning ? (
        <ReasoningPanel reasoning={metadata.reasoning} className="console-panel" />
      ) : null}

      {hasAssistantMessage ? (
        <Card className="console-panel space-y-2 p-4">
          <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
            Reasoning summary
          </p>
          <pre className="border-border/50 bg-muted/25 max-h-72 overflow-auto rounded-lg border p-3 text-sm leading-relaxed whitespace-pre-wrap">
            {assistantMessage}
          </pre>
        </Card>
      ) : null}

      {hasResults ? (
        <Card className="console-panel p-4">
          <p className="text-muted-foreground mb-3 text-xs font-medium tracking-wide uppercase">
            Results
          </p>
          <ChartPanel chart={chart} results={results} />
        </Card>
      ) : null}

      {showTrustPanel ? (
        <TrustPanel
          className="console-panel"
          title="Query trust & explainability"
          sql={sql}
          sources={sources}
          metadata={metadata}
          subtitle="Provenance, scope, and execution details for this query."
        />
      ) : (
        <>
          {sql ? (
            <Card className="console-panel space-y-2 p-4">
              <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
                Generated SQL
              </p>
              <pre className="border-border/50 bg-muted/25 max-h-72 overflow-auto rounded-lg border p-3 font-mono text-xs leading-relaxed">
                {sql}
              </pre>
            </Card>
          ) : null}
          <MetadataPanel metadata={metadata} title="Query metadata" />
        </>
      )}
    </PageShell>
  );
}
