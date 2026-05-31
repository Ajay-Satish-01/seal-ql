'use client';

import { ChartPanel } from '@/components/dashboard/chart-panel';
import { PageShell } from '@/components/dashboard/page-shell';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useConnection } from '@/hooks/use-connection';
import { streamChat } from '@/lib/chat-api';
import { notifyErrorFrom, notifyInfo, notifySuccess } from '@/lib/toast';
import type { ChartSpec } from 'seal';
import { useRef, useState, useTransition } from 'react';

type ChatTurn = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
};

function turnId(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `turn-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export default function ChatPage() {
  const { apiUrl, apiKey } = useConnection();
  const [message, setMessage] = useState('What tables are in the database?');
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [history, setHistory] = useState<ChatTurn[]>([]);
  const [answer, setAnswer] = useState('');
  const [sql, setSql] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, unknown>[]>([]);
  const [chart, setChart] = useState<ChartSpec | null>(null);
  const [isPending, startTransition] = useTransition();
  const abortRef = useRef<AbortController | null>(null);

  function send() {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const userMessage = message.trim();
    if (!userMessage) {
      notifyInfo('Enter a message first');
      return;
    }

    setAnswer('');
    setSql(null);
    setResults([]);
    setChart(null);
    setHistory((prev) => [...prev, { id: turnId(), role: 'user', content: userMessage }]);

    startTransition(async () => {
      let streamed = '';
      try {
        for await (const event of streamChat(
          apiUrl,
          { message: userMessage, session_id: sessionId, include_charts: true, enhancement: true },
          apiKey.trim(),
          controller.signal,
        )) {
          if (event.type === 'meta') {
            setSessionId(event.data.session_id);
            setSql(event.data.sql ?? null);
            if (event.data.results?.length) setResults(event.data.results);
            if (event.data.chart) setChart(event.data.chart as unknown as ChartSpec);
          } else if (event.type === 'delta') {
            streamed += event.content;
            setAnswer((prev) => prev + event.content);
          }
        }
        if (streamed) {
          setHistory((prev) => [...prev, { id: turnId(), role: 'assistant', content: streamed }]);
          notifySuccess('Chat response complete');
        }
      } catch (e) {
        if ((e as Error).name !== 'AbortError') {
          notifyErrorFrom(e, 'Chat failed');
        }
      }
    });
  }

  return (
    <PageShell title="Chat" description="POST /v1/chat with SSE streaming against your live API.">
      {history.length > 0 && (
        <Card className="console-panel max-h-64 space-y-3 overflow-y-auto p-4">
          {history.map((turn) => (
            <div key={turn.id} className="text-sm">
              <span className="text-primary text-xs font-medium tracking-wide uppercase">
                {turn.role}
              </span>
              <p className="mt-1 leading-relaxed whitespace-pre-wrap">{turn.content}</p>
            </div>
          ))}
        </Card>
      )}

      <Card className="console-panel space-y-4 p-4">
        {sessionId && (
          <p className="text-muted-foreground font-mono text-xs">Session: {sessionId}</p>
        )}
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={3}
          className="border-input bg-background w-full rounded-md border px-3 py-2 text-sm"
        />
        <div className="flex gap-2">
          <Button onClick={send} disabled={isPending || !message.trim()}>
            {isPending ? 'Streaming…' : 'Send'}
          </Button>
          <Button variant="outline" onClick={() => abortRef.current?.abort()} disabled={!isPending}>
            Stop
          </Button>
        </div>
      </Card>

      {answer && (
        <Card className="console-panel p-4">
          <p className="text-muted-foreground mb-2 text-xs font-medium tracking-wide uppercase">
            Assistant
          </p>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{answer}</p>
        </Card>
      )}

      {sql && (
        <Card className="console-panel p-4">
          <p className="text-muted-foreground mb-2 text-xs font-medium tracking-wide uppercase">
            SQL
          </p>
          <pre className="overflow-x-auto font-mono text-xs">{sql}</pre>
        </Card>
      )}

      {chart && (
        <Card className="console-panel p-4">
          <ChartPanel chart={chart} results={results} />
        </Card>
      )}
    </PageShell>
  );
}
