'use client';

import { useState } from 'react';
import type { QueryResponse } from 'seal';
import { CodeBlock } from '@/components/code-block';
import { ChartPanel } from './chart-panel';
import { MetadataPanel } from '@/components/demo/metadata-panel';
import type { ExecutionMetadata } from '@/lib/execution-metadata';
import { isDemoTrustExplainabilityEnabled } from '@/lib/demo-trust';
import { shouldShowTrustPanel } from '@seal/trust-explainability';
import { TrustPanel } from '@/components/demo/trust-panel';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface ResultsPanelProps {
  response: QueryResponse;
}

export function ResultsPanel({ response }: ResultsPanelProps) {
  const [sqlOpen, setSqlOpen] = useState(true);
  const meta = (response.metadata ?? {}) as Record<string, unknown>;
  const trustEnabled = isDemoTrustExplainabilityEnabled();
  const metadata = response.metadata as ExecutionMetadata | undefined;
  const showTrustPanel = shouldShowTrustPanel(trustEnabled, {
    sql: response.sql,
    sources: response.sources,
    metadata,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-3 text-xs">
        <span className="bg-muted rounded-md px-2 py-1 font-mono">
          {String(meta.row_count ?? response.results.length)} rows
        </span>
        <span className="bg-muted rounded-md px-2 py-1 font-mono">
          {String(meta.execution_time_ms ?? '—')} ms
        </span>
        {meta.truncated ? (
          <span className="rounded-md bg-amber-500/15 px-2 py-1 font-mono text-amber-800 dark:text-amber-200">
            truncated
          </span>
        ) : null}
      </div>

      {showTrustPanel ? (
        <TrustPanel
          title="Query trust & explainability"
          sql={response.sql}
          sources={response.sources}
          metadata={metadata}
          subtitle="Simulated fixture output when SEAL_TRUST_EXPLAINABILITY_ENABLED is on."
        />
      ) : (
        <>
          <div>
            <button
              type="button"
              onClick={() => setSqlOpen(!sqlOpen)}
              className="text-foreground mb-2 flex items-center gap-1 text-sm font-semibold"
            >
              {sqlOpen ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              Generated SQL
            </button>
            {sqlOpen ? <CodeBlock language="sql" code={response.sql} /> : null}
          </div>
          <MetadataPanel metadata={metadata} title="Query metadata" />
        </>
      )}

      <div>
        <h3 className="text-foreground mb-3 text-sm font-semibold">Visualization</h3>
        <ChartPanel chart={response.chart ?? null} results={response.results} />
      </div>
    </div>
  );
}
