'use client';

import { chatStreamErrorDemo } from '@/lib/demo-chat-fixtures';

export function ChatStreamErrorCallout() {
  const streamError = chatStreamErrorDemo();

  return (
    <div className="border-destructive/40 bg-destructive/5 rounded-md border p-4">
      <p className="text-foreground mb-1 text-sm font-semibold">
        Mid-stream failure (event: seal.error → stream_error)
      </p>
      <p className="text-muted-foreground font-mono text-xs">code: {streamError.code}</p>
      <p className="text-destructive mt-2 text-sm">{streamError.message}</p>
    </div>
  );
}
