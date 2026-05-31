'use client';

import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { Button } from './ui/button';
import { cn } from '@/lib/utils';

interface CodeBlockProps {
  code: string;
  language?: string;
}

export function CodeBlock({ code, language = 'bash' }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={cn(
        'not-prose group border-border/60 relative my-6 overflow-hidden rounded-xl border',
        'bg-zinc-950 text-zinc-50 dark:border-border/50 dark:bg-black/50',
      )}
    >
      <div
        className={cn(
          'border-border/50 flex items-center justify-between border-b px-4 py-2 text-xs',
          'bg-zinc-900 text-zinc-400 dark:bg-black/80',
        )}
      >
        <span className="font-mono uppercase">{language}</span>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-50"
          onClick={onCopy}
        >
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
          <span className="sr-only">Copy code</span>
        </Button>
      </div>
      <div className="overflow-x-auto p-4 font-mono text-sm leading-relaxed text-zinc-50">
        <pre className="m-0 bg-transparent p-0">
          <code className="bg-transparent text-inherit">{code}</code>
        </pre>
      </div>
    </div>
  );
}
