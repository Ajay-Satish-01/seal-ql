'use client';

import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { streamChat } from '@/lib/chat-api';
import { cn } from '@/lib/utils';

interface ChatStreamPanelProps {
  baseUrl: string;
  apiKey: string;
  disabled?: boolean;
}

export function ChatStreamPanel({ baseUrl, apiKey, disabled }: ChatStreamPanelProps) {
  const [message, setMessage] = useState('Summarize revenue trends.');
  const [tokens, setTokens] = useState('');
  const [metaJson, setMetaJson] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const pendingTokensRef = useRef('');
  const rafRef = useRef<number | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const errorId = useId();
  const liveId = useId();

  const canStream = !disabled && baseUrl.trim().length > 0 && !loading;

  const clearFlushTimers = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const flushTokens = useCallback(() => {
    clearFlushTimers();
    if (!pendingTokensRef.current) return;
    const chunk = pendingTokensRef.current;
    pendingTokensRef.current = '';
    setTokens((t) => t + chunk);
  }, [clearFlushTimers]);

  const scheduleTokenFlush = useCallback(() => {
    // rAF keeps updates smooth when visible; the timeout is a fallback for
    // background tabs where rAF is paused so tokens still render periodically.
    if (rafRef.current === null) {
      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = null;
        flushTokens();
      });
    }
    if (timeoutRef.current === null) {
      timeoutRef.current = setTimeout(() => {
        timeoutRef.current = null;
        flushTokens();
      }, 100);
    }
  }, [flushTokens]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      clearFlushTimers();
    };
  }, [clearFlushTimers]);

  const stream = useCallback(async () => {
    if (!baseUrl.trim()) {
      setError('Enter an API base URL above.');
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    setTokens('');
    setMetaJson(null);
    pendingTokensRef.current = '';

    try {
      for await (const event of streamChat(
        baseUrl,
        { message, include_charts: true },
        apiKey || undefined,
        controller.signal,
      )) {
        if (controller.signal.aborted) break;
        if (event.type === 'meta') {
          flushTokens();
          setMetaJson(JSON.stringify(event.data, null, 2));
        } else if (event.type === 'delta') {
          pendingTokensRef.current += event.content;
          scheduleTokenFlush();
        }
      }
      flushTokens();
    } catch (e) {
      if (controller.signal.aborted) return;
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (abortRef.current === controller) {
        setLoading(false);
      }
    }
  }, [apiKey, baseUrl, flushTokens, message, scheduleTokenFlush]);

  return (
    <div className="border-border/60 bg-card/40 flex flex-col gap-3 rounded-lg border p-4">
      <label className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
        Streaming (SSE)
      </label>
      <input
        className="border-border bg-background w-full rounded-md border px-3 py-2 text-sm"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        disabled={loading}
        aria-describedby={error ? errorId : undefined}
        aria-invalid={Boolean(error)}
      />
      <button
        type="button"
        onClick={() => void stream()}
        disabled={!canStream}
        aria-busy={loading}
        className={cn(
          'bg-secondary text-secondary-foreground rounded-sm px-4 py-2 text-sm font-medium',
          !canStream && 'cursor-not-allowed opacity-60',
        )}
      >
        {loading ? 'Streaming…' : 'Stream'}
      </button>
      {error ? (
        <p id={errorId} className="text-destructive text-sm" role="alert">
          {error}
        </p>
      ) : null}
      {metaJson ? (
        <pre className="text-muted-foreground max-h-32 overflow-auto font-mono text-xs">{metaJson}</pre>
      ) : null}
      {loading || tokens ? (
        <div
          id={liveId}
          className="border-border/40 bg-muted/30 min-h-[2.5rem] rounded-md border p-3 text-sm whitespace-pre-wrap"
          aria-live="polite"
          aria-busy={loading}
        >
          {tokens || (loading ? 'Waiting for response…' : '')}
        </div>
      ) : null}
    </div>
  );
}
