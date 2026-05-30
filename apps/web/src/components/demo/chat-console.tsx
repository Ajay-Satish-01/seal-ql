'use client';

import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { postChat, type ChatApiResponse } from '@/lib/chat-api';
import { cn } from '@/lib/utils';

interface ChatConsoleProps {
  baseUrl: string;
  apiKey: string;
  disabled?: boolean;
}

export function ChatConsole({ baseUrl, apiKey, disabled }: ChatConsoleProps) {
  const [message, setMessage] = useState('What tables are in the database?');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [includeCharts, setIncludeCharts] = useState(false);
  const [enhancement, setEnhancement] = useState(true);
  const [answer, setAnswer] = useState<ChatApiResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const errorId = useId();
  const liveId = useId();

  const canSend = !disabled && baseUrl.trim().length > 0 && !loading;

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const send = useCallback(async () => {
    if (!baseUrl.trim()) {
      setError('Enter an API base URL above.');
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);

    try {
      const res = await postChat(
        baseUrl,
        {
          message,
          session_id: sessionId ?? undefined,
          include_charts: includeCharts,
          enhancement,
        },
        apiKey || undefined,
        controller.signal,
      );
      if (controller.signal.aborted) return;
      setSessionId(res.session_id);
      setAnswer(res);
    } catch (e) {
      if (controller.signal.aborted) return;
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (abortRef.current === controller) {
        setLoading(false);
      }
    }
  }, [apiKey, baseUrl, enhancement, includeCharts, message, sessionId]);

  return (
    <div className="border-border/60 bg-card/40 flex flex-col gap-4 rounded-lg border p-4">
      <label className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
        Live chat
      </label>
      <textarea
        className="border-border bg-background min-h-[80px] w-full rounded-md border px-3 py-2 text-sm"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        disabled={loading}
        aria-describedby={error ? errorId : undefined}
        aria-invalid={Boolean(error)}
      />
      <div className="flex flex-wrap gap-4 text-sm">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={includeCharts}
            onChange={(e) => setIncludeCharts(e.target.checked)}
            disabled={loading}
          />
          Charts
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={enhancement}
            onChange={(e) => setEnhancement(e.target.checked)}
            disabled={loading}
          />
          Enhancement
        </label>
      </div>
      {sessionId ? (
        <p className="text-muted-foreground font-mono text-xs">session: {sessionId}</p>
      ) : null}
      <button
        type="button"
        onClick={() => void send()}
        disabled={!canSend}
        aria-busy={loading}
        className={cn(
          'bg-primary text-primary-foreground rounded-sm px-4 py-2 text-sm font-medium',
          !canSend && 'cursor-not-allowed opacity-60',
        )}
      >
        {loading ? 'Sending…' : 'Send'}
      </button>
      {error ? (
        <p id={errorId} className="text-destructive text-sm" role="alert">
          {error}
        </p>
      ) : null}
      {loading || answer ? (
        <div
          id={liveId}
          className="border-border/40 bg-muted/30 min-h-[2.5rem] space-y-3 rounded-md border p-3 text-sm"
          aria-live="polite"
          aria-busy={loading}
        >
          {loading && !answer ? (
            <p className="text-muted-foreground">Waiting for response…</p>
          ) : null}
          {answer ? <p className="whitespace-pre-wrap">{answer.message}</p> : null}
          {answer?.sql ? (
            <pre className="text-muted-foreground overflow-x-auto font-mono text-xs">{answer.sql}</pre>
          ) : null}
          {answer?.sources && answer.sources.length > 0 ? (
            <p className="text-muted-foreground text-xs">
              sources: {answer.sources.join(', ')}
            </p>
          ) : null}
          {answer?.chart ? (
            <p className="text-muted-foreground text-xs">
              chart: {String((answer.chart as { chart_type?: string }).chart_type ?? 'attached')}
            </p>
          ) : null}
          {answer?.results && answer.results.length > 0 ? (
            <pre className="text-muted-foreground max-h-40 overflow-auto font-mono text-xs">
              {JSON.stringify(answer.results.slice(0, 5), null, 2)}
              {answer.results.length > 5 ? '\n…' : ''}
            </pre>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
