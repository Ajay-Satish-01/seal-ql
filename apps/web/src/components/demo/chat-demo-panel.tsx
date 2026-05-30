'use client';

import type { ChatApiResponse } from '@/lib/chat-api';
import { Badge } from '@/components/ui/badge';
import { CodeBlock } from '@/components/code-block';
import { ChartPanel } from './chart-panel';
import type { ChartSpec } from 'seal';

interface ChatDemoPanelProps {
  message: string;
  response: ChatApiResponse;
}

export function ChatDemoPanel({ message, response }: ChatDemoPanelProps) {
  const chart = response.chart as ChartSpec | null | undefined;
  const results = (response.results ?? []) as Record<string, unknown>[];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-foreground text-sm font-semibold tracking-wider uppercase">
          Chat response
        </h3>
        <Badge variant="outline" className="text-xs">
          Simulated
        </Badge>
      </div>

      <div className="border-border/50 bg-card/50 rounded-lg border p-4">
        <p className="text-muted-foreground mb-1 text-xs font-medium uppercase">User message</p>
        <p className="text-sm leading-relaxed">&ldquo;{message}&rdquo;</p>
      </div>

      <p className="text-muted-foreground font-mono text-xs">session: {response.session_id}</p>

      <div className="border-border/40 bg-muted/30 space-y-3 rounded-md border p-4 text-sm">
        <p className="whitespace-pre-wrap">{response.message}</p>
        {response.sources && response.sources.length > 0 ? (
          <p className="text-muted-foreground text-xs">sources: {response.sources.join(', ')}</p>
        ) : null}
      </div>

      {response.sql ? (
        <div>
          <p className="text-foreground mb-2 text-sm font-semibold">Executed SQL</p>
          <CodeBlock language="sql" code={response.sql} />
        </div>
      ) : null}

      {chart ? (
        <div>
          <p className="text-foreground mb-3 text-sm font-semibold">Chart (include_charts)</p>
          <ChartPanel chart={chart} results={results} />
        </div>
      ) : null}
    </div>
  );
}
