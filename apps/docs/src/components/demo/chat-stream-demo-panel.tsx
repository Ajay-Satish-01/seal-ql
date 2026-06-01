'use client';

import type { ChatStreamDemo } from '@/lib/demo-chat-fixtures';
import { Badge } from '@/components/ui/badge';
import { MetadataJsonBlock } from '@/components/docs/metadata-json-block';
import { formatMetadataJson } from '@/lib/execution-metadata';
import { CodeBlock } from '@/components/code-block';

interface ChatStreamDemoPanelProps {
  demo: ChatStreamDemo;
}

export function ChatStreamDemoPanel({ demo }: ChatStreamDemoPanelProps) {
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

      <MetadataJsonBlock title="event: seal.meta" code={formatMetadataJson(demo.meta)} />

      <div>
        <p className="text-foreground mb-2 text-sm font-semibold">Answer tokens (data: chunks)</p>
        <div className="border-border/40 bg-muted/30 rounded-md border p-4 text-sm whitespace-pre-wrap">
          {demo.answerText}
        </div>
      </div>
    </div>
  );
}
