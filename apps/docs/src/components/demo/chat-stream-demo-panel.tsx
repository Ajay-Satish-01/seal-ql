'use client';

import type { ChatStreamDemo } from '@/lib/demo-chat-fixtures';
import { Badge } from '@/components/ui/badge';
import { MetadataJsonBlock } from '@/components/docs/metadata-json-block';
import { isDemoTrustExplainabilityEnabled } from '@/lib/demo-trust';
import { formatMetadataJson } from '@/lib/execution-metadata';
import { shouldShowTrustPanel } from '@seal/trust-explainability';
import { TrustPanel } from '@/components/demo/trust-panel';

interface ChatStreamDemoPanelProps {
  demo: ChatStreamDemo;
}

export function ChatStreamDemoPanel({ demo }: ChatStreamDemoPanelProps) {
  const trustEnabled = isDemoTrustExplainabilityEnabled();
  const showTrustPanel = shouldShowTrustPanel(trustEnabled, {
    sql: demo.meta.sql,
    sources: demo.meta.sources ?? undefined,
    metadata: demo.meta,
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-foreground text-sm font-semibold tracking-wider uppercase">
          Streaming (SSE)
        </h3>
        <Badge variant="outline" className="text-xs">
          Simulated
        </Badge>
      </div>

      <div className="border-border/50 bg-card/50 rounded-lg border p-4">
        <p className="text-muted-foreground mb-1 text-xs font-medium uppercase">User message</p>
        <p className="text-sm leading-relaxed">&ldquo;{demo.message}&rdquo;</p>
      </div>

      {showTrustPanel ? (
        <TrustPanel
          title="seal.meta trust surface"
          sql={demo.meta.sql}
          sources={demo.meta.sources ?? undefined}
          metadata={demo.meta}
          subtitle="Flat SSE seal.meta payload with trust explainability fields."
        />
      ) : (
        <MetadataJsonBlock title="event: seal.meta" code={formatMetadataJson(demo.meta)} />
      )}

      <div>
        <p className="text-foreground mb-2 text-sm font-semibold">Answer tokens (data: chunks)</p>
        <div className="border-border/40 bg-muted/30 rounded-md border p-4 text-sm whitespace-pre-wrap">
          {demo.answerText}
        </div>
      </div>

      {demo.streamError ? (
        <div className="border-destructive/40 bg-destructive/5 rounded-md border p-4">
          <p className="text-foreground mb-1 text-sm font-semibold">
            event: seal.error → stream_error
          </p>
          <p className="text-muted-foreground font-mono text-xs">
            code: {demo.streamError.code}
          </p>
          <p className="text-destructive mt-2 text-sm">{demo.streamError.message}</p>
        </div>
      ) : null}
    </div>
  );
}
