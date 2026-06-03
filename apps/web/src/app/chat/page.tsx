'use client';

import { ChartPanel } from '@/components/dashboard/chart-panel';
import { MetadataPanel } from '@/components/dashboard/metadata-panel';
import { PageShell } from '@/components/dashboard/page-shell';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useChatSessionList } from '@/contexts/chat-session-context';
import { useConnection } from '@/hooks/use-connection';
import { streamChat, type ChatStreamMeta } from '@/lib/chat-api';
import type { ChatMetadata } from '@/lib/execution-metadata';
import { chatMetadataFromPartial, chatMetadataFromStreamMeta } from '@/lib/metadata-from-stream';
import { getSession } from '@/lib/session-api';
import { notifyErrorFrom, notifyInfo, notifySuccess } from '@/lib/toast';
import type { ChartSpec } from 'seal';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useCallback, useEffect, useRef, useState, useTransition } from 'react';

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

function clearTurnState() {
  return {
    answer: '',
    sql: null as string | null,
    results: [] as Record<string, unknown>[],
    chart: null as ChartSpec | null,
    metadata: null as ChatMetadata | null,
    sources: [] as string[],
  };
}

export default function ChatPageWrapper() {
  return (
    <Suspense>
      <ChatPage />
    </Suspense>
  );
}

function ChatPage() {
  const { apiUrl, apiKey, databaseId } = useConnection();
  const { refreshSessions } = useChatSessionList();
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlSessionId = searchParams.get('session') ?? undefined;

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
  const [loadingSession, setLoadingSession] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const prevDatabaseRef = useRef(databaseId);
  const loadedSessionUrlRef = useRef<string | undefined>(undefined);

  const resetConversation = useCallback(() => {
    loadedSessionUrlRef.current = undefined;
    const cleared = clearTurnState();
    setSessionId(undefined);
    setActiveDatabaseId(undefined);
    setHistory([]);
    setAnswer(cleared.answer);
    setSql(cleared.sql);
    setResults(cleared.results);
    setChart(cleared.chart);
    setMetadata(cleared.metadata);
    setSources(cleared.sources);
  }, []);

  useEffect(() => {
    if (!urlSessionId) {
      loadedSessionUrlRef.current = undefined;
      resetConversation();
      return;
    }
    if (loadedSessionUrlRef.current === urlSessionId) {
      return;
    }

    let cancelled = false;
    setLoadingSession(true);
    void (async () => {
      try {
        const detail = await getSession(apiUrl, urlSessionId, apiKey.trim() || undefined);
        if (cancelled) return;
        const turns: ChatTurn[] = detail.messages.map((m) => ({
          id: turnId(),
          role: m.role as 'user' | 'assistant',
          content: m.content,
        }));
        const cleared = clearTurnState();
        setSessionId(detail.session_id);
        setActiveDatabaseId(detail.database_id ?? undefined);
        setHistory(turns);
        setAnswer(cleared.answer);
        setSql(cleared.sql);
        setResults(cleared.results);
        setChart(cleared.chart);
        setMetadata(cleared.metadata);
        setSources(cleared.sources);
        loadedSessionUrlRef.current = urlSessionId;
      } catch (e) {
        if (!cancelled) {
          notifyErrorFrom(e, 'Failed to load chat session');
          loadedSessionUrlRef.current = undefined;
          router.push('/chat');
        }
      } finally {
        if (!cancelled) setLoadingSession(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [urlSessionId, apiUrl, apiKey, router, resetConversation]);

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
    router.push('/chat');
    resetConversation();
    notifyInfo(`Database changed to "${databaseId}" — chat session cleared`);
  }, [databaseId, sessionId, history, activeDatabaseId, router, resetConversation]);

  function applyStreamMeta(data: ChatStreamMeta) {
    setSessionId(data.session_id);
    if (data.database_id) setActiveDatabaseId(data.database_id);
    setSql(data.sql ?? null);
    if (data.results?.length) setResults(data.results);
    if (data.chart) setChart(data.chart as unknown as ChartSpec);
    if (data.sources?.length) setSources(data.sources);
    setMetadata(chatMetadataFromStreamMeta(data));
    if (!urlSessionId || urlSessionId !== data.session_id) {
      router.replace(`/chat?session=${encodeURIComponent(data.session_id)}`);
    }
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

    const cleared = clearTurnState();
    setAnswer(cleared.answer);
    setSql(cleared.sql);
    setResults(cleared.results);
    setChart(cleared.chart);
    setMetadata(cleared.metadata);
    setSources(cleared.sources);
    setHistory((prev) => [...prev, { id: turnId(), role: 'user', content: userMessage }]);
    setMessage('');

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
          refreshSessions();
        }
      } catch (e) {
        if ((e as Error).name !== 'AbortError') {
          notifyErrorFrom(e, 'Chat failed');
        }
      }
    });
  }

  function newSession() {
    router.push('/chat');
    resetConversation();
    notifyInfo('Started a new chat session');
  }

  return (
    <PageShell
      title="Chat"
      description={`POST /v1/chat (SSE) on database "${databaseId}" — execution metadata arrives on seal.meta before token deltas.`}
    >
      {loadingSession && (
        <p className="text-muted-foreground text-sm">Loading conversation…</p>
      )}

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
          disabled={loadingSession}
        />
        <div className="flex flex-wrap gap-2">
          <Button onClick={send} disabled={isPending || !message.trim() || loadingSession}>
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
