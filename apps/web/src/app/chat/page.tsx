'use client';

import { ChartPanel } from '@/components/dashboard/chart-panel';
import { MetadataPanel } from '@/components/dashboard/metadata-panel';
import { PageShell } from '@/components/dashboard/page-shell';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useConnection } from '@/hooks/use-connection';
import { streamChat, type ChatStreamMeta } from '@/lib/chat-api';
import type { ChatMetadata } from '@/lib/execution-metadata';
import { chatMetadataFromPartial, chatMetadataFromStreamMeta } from '@/lib/metadata-from-stream';
import { notifyErrorFrom, notifyInfo, notifySuccess } from '@/lib/toast';
import type { ChartSpec } from 'seal';
import { useEffect, useRef, useState, useTransition } from 'react';

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
  const { apiUrl, apiKey, databaseId } = useConnection();
  const [message, setMessage] = useState('What tables are in the database?');
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [activeDatabaseId, setActiveDatabaseId] = useState<string | undefined>();
  const [history, setHistory] = useState<ChatTurn[]>([]);
  const [answer, setAnswer] = useState('');
  const [sql, setSql] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, unknown>[]>([]);
  const [chart, setChart] = useState<ChartSpec | null>(null);
  const [metadata, setMetadata] = useState<ChatMetadata | null>(null);
  const [sources, setSources] = useState<string[]>([]);
  const [isPending, startTransition] = useTransition();
  const abortRef = useRef<AbortController | null>(null);
  const prevDatabaseRef = useRef(databaseId);

  useEffect(() => {
    if (prevDatabaseRef.current === databaseId) {
      return;
    }
    const hadSession =
      sessionId !== undefined || history.length > 0 || activeDatabaseId !== undefined;
    prevDatabaseRef.current = databaseId;
    if (!hadSession) {
      return;
    }
    setSessionId(undefined);
    setActiveDatabaseId(undefined);
    setHistory([]);
    setAnswer('');
    setSql(null);
    setResults([]);
    setChart(null);
    setMetadata(null);
    setSources([]);
    notifyInfo(`Database changed to "${databaseId}" — chat session cleared`);
  }, [databaseId, sessionId, history, activeDatabaseId]);

  function applyStreamMeta(data: ChatStreamMeta) {
    setSessionId(data.session_id);
    if (data.database_id) setActiveDatabaseId(data.database_id);
    setSql(data.sql ?? null);
    if (data.results?.length) setResults(data.results);
    if (data.chart) setChart(data.chart as unknown as ChartSpec);
    if (data.sources?.length) setSources(data.sources);
    setMetadata(chatMetadataFromStreamMeta(data));
  }

  function applyPartialStreamMeta(partial: Partial<ChatStreamMeta>) {
    if (partial.session_id) setSessionId(partial.session_id);
    if (partial.database_id) setActiveDatabaseId(partial.database_id);
    if (partial.sources?.length) setSources(partial.sources);
    if (typeof partial.sql === 'string') setSql(partial.sql);
  }

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
    setMetadata(null);
    setSources([]);
    setHistory((prev) => [...prev, { id: turnId(), role: 'user', content: userMessage }]);

    startTransition(async () => {
      let streamed = '';
      try {
        for await (const event of streamChat(
          apiUrl,
          {
            message: userMessage,
            session_id: sessionId,
            database_id: databaseId,
            include_charts: true,
            enhancement: true,
          },
          apiKey.trim(),
          controller.signal,
        )) {
          if (event.type === 'meta') {
            applyStreamMeta(event.data);
          } else if (event.type === 'meta_error') {
            applyPartialStreamMeta(event.partial);
            const partialMeta = chatMetadataFromPartial(event.partial);
            if (partialMeta) setMetadata(partialMeta);
            notifyInfo(`seal.meta validation: ${event.error}`);
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

  function newSession() {
    setSessionId(undefined);
    setActiveDatabaseId(undefined);
    setHistory([]);
    setAnswer('');
    setSql(null);
    setResults([]);
    setChart(null);
    setMetadata(null);
    setSources([]);
    notifyInfo('Started a new chat session');
  }

  return (
    <PageShell
      title="Chat"
      description={`POST /v1/chat (SSE) on database "${databaseId}" — execution metadata arrives on seal.meta before token deltas.`}
    >
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
        <div className="text-muted-foreground flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs">
          <span>database_id: {activeDatabaseId ?? databaseId}</span>
          {sessionId && <span>session: {sessionId}</span>}
          {sources.length > 0 && <span>sources: {sources.join(', ')}</span>}
        </div>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={3}
          className="border-input bg-background w-full rounded-md border px-3 py-2 text-sm"
        />
        <div className="flex flex-wrap gap-2">
          <Button onClick={send} disabled={isPending || !message.trim()}>
            {isPending ? 'Streaming…' : 'Send'}
          </Button>
          <Button variant="outline" onClick={() => abortRef.current?.abort()} disabled={!isPending}>
            Stop
          </Button>
          <Button variant="outline" onClick={newSession} disabled={isPending}>
            New session
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

      <MetadataPanel
        metadata={metadata}
        subtitle="From SSE seal.meta (flat JSON). JSON chat uses the same fields under metadata."
      />

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
