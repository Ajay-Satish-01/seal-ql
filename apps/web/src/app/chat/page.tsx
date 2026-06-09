'use client';

import { ChartPanel } from '@/components/dashboard/chart-panel';
import { ReasoningPanel } from '@/components/dashboard/reasoning-panel';
import {
  ExplainabilityTrigger,
  shouldRenderExplainabilityTrigger,
  TrustExplainabilityDialog,
  type ExplainabilitySurface,
} from '@/components/dashboard/trust-explainability-dialog';
import { PageShell } from '@/components/dashboard/page-shell';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useChatSessionList } from '@/contexts/chat-session-context';
import { useConnection } from '@/hooks/use-connection';
import { streamChat, type ChatStreamMeta } from '@/lib/chat-api';
import type { ChatMetadata } from '@/lib/execution-metadata';
import { chatMetadataFromPartial, chatMetadataFromStreamMeta } from '@/lib/metadata-from-stream';
import { getSession, type SessionMessageExplainability } from '@/lib/session-api';
import { notifyErrorFrom, notifyInfo, notifySuccess } from '@/lib/toast';
import type { ChartSpec } from 'seal';
import { useRouter, useSearchParams } from 'next/navigation';
import { memo, Suspense, useCallback, useEffect, useRef, useState, useTransition } from 'react';

type TurnExplainability = {
  sql: string | null;
  sources: string[];
  metadata: ChatMetadata | null;
  chart: ChartSpec | null;
  results: Record<string, unknown>[];
};

type UserTurn = {
  id: string;
  role: 'user';
  content: string;
};

type AssistantTurn = {
  id: string;
  role: 'assistant';
  content: string;
  explainability: TurnExplainability;
};

type ChatTurn = UserTurn | AssistantTurn;

type PendingAssistant = {
  content: string;
  explainability: TurnExplainability;
};

function turnId(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `turn-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function emptyExplainability(): TurnExplainability {
  return {
    sql: null,
    sources: [],
    metadata: null,
    chart: null,
    results: [],
  };
}

function explainabilityFromStreamMeta(data: ChatStreamMeta): TurnExplainability {
  return {
    sql: data.sql ?? null,
    sources: data.sources ?? [],
    metadata: chatMetadataFromStreamMeta(data),
    chart: data.chart ? (data.chart as unknown as ChartSpec) : null,
    results: data.results ?? [],
  };
}

function explainabilityFromSession(
  stored: SessionMessageExplainability | null | undefined,
): TurnExplainability {
  if (!stored) return emptyExplainability();
  return {
    sql: stored.sql ?? null,
    sources: stored.sources ?? [],
    metadata: (stored.metadata as ChatMetadata | null) ?? null,
    chart: stored.chart ? (stored.chart as unknown as ChartSpec) : null,
    results: stored.results ?? [],
  };
}

function mergePartialExplainability(
  current: TurnExplainability,
  partial: Partial<ChatStreamMeta>,
): TurnExplainability {
  const next = { ...current };
  if (partial.sources?.length) next.sources = partial.sources;
  if (typeof partial.sql === 'string') next.sql = partial.sql;
  const partialMeta = chatMetadataFromPartial(partial);
  if (partialMeta) {
    next.metadata = { ...(next.metadata ?? {}), ...partialMeta };
  }
  return next;
}

export default function ChatPageWrapper() {
  return (
    <Suspense>
      <ChatPage />
    </Suspense>
  );
}

const AssistantMessage = memo(function AssistantMessage({
  content,
  explainability,
  trustExplainabilityEnabled,
  onOpenExplainability,
  streaming = false,
  explainabilityPending = false,
}: {
  content: string;
  explainability: TurnExplainability;
  trustExplainabilityEnabled: boolean;
  onOpenExplainability: (surface: ExplainabilitySurface) => void;
  streaming?: boolean;
  explainabilityPending?: boolean;
}) {
  const showExplainability = shouldRenderExplainabilityTrigger(
    trustExplainabilityEnabled,
    explainability,
  );

  return (
    <div className="border-border/50 bg-muted/15 space-y-3 rounded-lg border px-3 py-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <span className="text-primary text-xs font-medium tracking-wide uppercase">assistant</span>
        {showExplainability ? (
          <ExplainabilityTrigger
            disabled={explainabilityPending}
            onClick={() => onOpenExplainability(explainability)}
          />
        ) : null}
      </div>
      {content ? (
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
      ) : streaming ? (
        <p className="text-muted-foreground text-sm">Streaming…</p>
      ) : null}
      <ReasoningPanel reasoning={explainability.metadata?.reasoning} />
      {explainability.chart ? (
        <ChartPanel chart={explainability.chart} results={explainability.results} />
      ) : null}
    </div>
  );
});

function ChatPage() {
  const { apiUrl, apiKey, databaseId, trustExplainabilityEnabled } = useConnection();
  const { refreshSessions } = useChatSessionList();
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlSessionId = searchParams.get('session') ?? undefined;

  const [message, setMessage] = useState('What tables are in the database?');
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [activeDatabaseId, setActiveDatabaseId] = useState<string | undefined>();
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [pendingAssistant, setPendingAssistant] = useState<PendingAssistant | null>(null);
  const [isPending, startTransition] = useTransition();
  const [loadingSession, setLoadingSession] = useState(false);
  const [explainabilityOpen, setExplainabilityOpen] = useState(false);
  const [activeExplainability, setActiveExplainability] = useState<ExplainabilitySurface | null>(
    null,
  );
  const abortRef = useRef<AbortController | null>(null);
  const prevDatabaseRef = useRef(databaseId);
  const loadedSessionUrlRef = useRef<string | undefined>(undefined);
  const pendingRef = useRef<PendingAssistant | null>(null);

  const setPending = useCallback((value: PendingAssistant | null) => {
    pendingRef.current = value;
    setPendingAssistant(value);
  }, []);

  const updatePending = useCallback(
    (updater: (prev: PendingAssistant | null) => PendingAssistant | null) => {
      setPendingAssistant((prev) => {
        const next = updater(prev);
        pendingRef.current = next;
        return next;
      });
    },
    [],
  );

  const resetConversation = useCallback(() => {
    loadedSessionUrlRef.current = undefined;
    setSessionId(undefined);
    setActiveDatabaseId(undefined);
    setTurns([]);
    pendingRef.current = null;
    setPendingAssistant(null);
    setExplainabilityOpen(false);
    setActiveExplainability(null);
  }, []);

  const openExplainability = useCallback((surface: ExplainabilitySurface) => {
    setActiveExplainability(surface);
    setExplainabilityOpen(true);
  }, []);

  const handleExplainabilityOpenChange = useCallback((open: boolean) => {
    setExplainabilityOpen(open);
  }, []);

  const handleExplainabilityAnimationComplete = useCallback((open: boolean) => {
    if (!open) setActiveExplainability(null);
  }, []);

  useEffect(() => {
    if (!urlSessionId) {
      loadedSessionUrlRef.current = undefined;
      queueMicrotask(resetConversation);
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
        const loaded: ChatTurn[] = detail.messages.map((m) => {
          if (m.role === 'assistant') {
            return {
              id: turnId(),
              role: 'assistant' as const,
              content: m.content,
              explainability: explainabilityFromSession(m.explainability),
            };
          }
          return {
            id: turnId(),
            role: 'user' as const,
            content: m.content,
          };
        });
        setSessionId(detail.session_id);
        setActiveDatabaseId(detail.database_id ?? undefined);
        setTurns(loaded);
        pendingRef.current = null;
        setPendingAssistant(null);
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
      sessionId !== undefined || turns.length > 0 || activeDatabaseId !== undefined;
    prevDatabaseRef.current = databaseId;
    if (!hadSession) {
      return;
    }
    router.push('/chat');
    queueMicrotask(() => {
      resetConversation();
      notifyInfo(`Database changed to "${databaseId}" — chat session cleared`);
    });
  }, [databaseId, sessionId, turns, activeDatabaseId, router, resetConversation]);

  function applyStreamMeta(data: ChatStreamMeta) {
    setSessionId(data.session_id);
    if (data.database_id) setActiveDatabaseId(data.database_id);
    updatePending((prev) =>
      prev
        ? { ...prev, explainability: explainabilityFromStreamMeta(data) }
        : { content: '', explainability: explainabilityFromStreamMeta(data) },
    );
    if (!urlSessionId || urlSessionId !== data.session_id) {
      // Pin before navigation so the session loader does not refetch and wipe in-flight state.
      loadedSessionUrlRef.current = data.session_id;
      router.replace(`/chat?session=${encodeURIComponent(data.session_id)}`);
    }
  }

  function applyPartialStreamMeta(partial: Partial<ChatStreamMeta>) {
    if (partial.session_id) setSessionId(partial.session_id);
    if (partial.database_id) setActiveDatabaseId(partial.database_id);
    updatePending((prev) => {
      const base = prev ?? { content: '', explainability: emptyExplainability() };
      return {
        ...base,
        explainability: mergePartialExplainability(base.explainability, partial),
      };
    });
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

    setTurns((prev) => [...prev, { id: turnId(), role: 'user', content: userMessage }]);
    setPending({ content: '', explainability: emptyExplainability() });
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
            notifyInfo(`seal.meta validation: ${event.error}`);
          } else if (event.type === 'stream_error') {
            setPending(null);
            setExplainabilityOpen(false);
            setActiveExplainability(null);
            notifyErrorFrom(new Error(event.message), event.message);
            return;
          } else if (event.type === 'delta') {
            streamed += event.content;
            updatePending((prev) =>
              prev ? { ...prev, content: prev.content + event.content } : null,
            );
          }
        }
        const final = pendingRef.current;
        const replyText = final?.content?.trim() || streamed.trim();
        if (final && replyText) {
          setTurns((history) => [
            ...history,
            {
              id: turnId(),
              role: 'assistant',
              content: final.content || streamed,
              explainability: final.explainability,
            },
          ]);
          notifySuccess('Chat response complete');
          refreshSessions();
        }
        setPending(null);
      } catch (e) {
        setPending(null);
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

  const activeSources = pendingAssistant?.explainability.sources ?? [];

  return (
    <PageShell
      title="Chat"
      description={`POST /v1/chat (SSE) on database "${databaseId}" — execution metadata arrives on seal.meta before token deltas.`}
    >
      {loadingSession && <p className="text-muted-foreground text-sm">Loading conversation…</p>}

      {(turns.length > 0 || pendingAssistant) && (
        <Card className="console-panel max-h-[32rem] space-y-4 overflow-y-auto p-4">
          {turns.map((turn) =>
            turn.role === 'user' ? (
              <div key={turn.id} className="text-sm">
                <span className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
                  user
                </span>
                <p className="mt-1 leading-relaxed whitespace-pre-wrap">{turn.content}</p>
              </div>
            ) : (
              <AssistantMessage
                key={turn.id}
                content={turn.content}
                explainability={turn.explainability}
                trustExplainabilityEnabled={trustExplainabilityEnabled}
                onOpenExplainability={openExplainability}
              />
            ),
          )}
          {pendingAssistant ? (
            <AssistantMessage
              content={pendingAssistant.content}
              explainability={pendingAssistant.explainability}
              trustExplainabilityEnabled={trustExplainabilityEnabled}
              onOpenExplainability={openExplainability}
              streaming={isPending}
              explainabilityPending={
                isPending &&
                !pendingAssistant.explainability.metadata &&
                !pendingAssistant.explainability.sql
              }
            />
          ) : null}
        </Card>
      )}

      <Card className="console-panel space-y-4 p-4">
        <div className="text-muted-foreground flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs">
          <span>database_id: {activeDatabaseId ?? databaseId}</span>
          {sessionId ? <span>session: {sessionId}</span> : null}
          {activeSources.length > 0 ? <span>sources: {activeSources.join(', ')}</span> : null}
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

      {activeExplainability ? (
        <TrustExplainabilityDialog
          open={explainabilityOpen}
          onOpenChange={handleExplainabilityOpenChange}
          onOpenChangeComplete={handleExplainabilityAnimationComplete}
          sql={activeExplainability.sql}
          sources={activeExplainability.sources}
          metadata={activeExplainability.metadata}
          chart={activeExplainability.chart}
          results={activeExplainability.results}
          trustExplainabilityEnabled={trustExplainabilityEnabled}
        />
      ) : null}
    </PageShell>
  );
}
