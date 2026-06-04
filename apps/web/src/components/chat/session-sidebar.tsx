'use client';

import { SessionItem } from '@/components/chat/session-item';
import { Button } from '@/components/ui/button';
import { useChatSessionList } from '@/contexts/chat-session-context';
import { useConnection } from '@/hooks/use-connection';
import { deleteSession, listSessions, type SessionSummary } from '@/lib/session-api';
import { notifyErrorFrom, notifyInfo } from '@/lib/toast';
import { Plus } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';

export function SessionSidebar() {
  const { apiUrl, apiKey, databaseId } = useConnection();
  const { refreshKey } = useChatSessionList();
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeSessionId = searchParams.get('session') ?? undefined;

  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setLoading(true);
      try {
        const { sessions: list } = await listSessions(
          apiUrl,
          apiKey.trim() || undefined,
          databaseId,
        );
        if (!cancelled) setSessions(list);
      } catch (e) {
        if (!cancelled) {
          notifyErrorFrom(e, 'Failed to load chat sessions');
          setSessions([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiUrl, apiKey, databaseId, refreshKey]);

  function startNewChat() {
    router.push('/chat');
  }

  function selectSession(sessionId: string) {
    router.push(`/chat?session=${encodeURIComponent(sessionId)}`);
  }

  async function handleDelete(sessionId: string) {
    if (!window.confirm('Delete this chat session? This cannot be undone.')) return;
    try {
      await deleteSession(apiUrl, sessionId, apiKey.trim() || undefined);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      if (activeSessionId === sessionId) {
        startNewChat();
      }
      notifyInfo('Chat deleted');
    } catch (e) {
      notifyErrorFrom(e, 'Failed to delete chat');
    }
  }

  return (
    <aside className="border-border bg-sidebar/50 flex w-56 shrink-0 flex-col border-r">
      <div className="border-border border-b p-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2"
          onClick={startNewChat}
        >
          <Plus className="h-4 w-4" />
          New chat
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {loading && sessions.length === 0 && (
          <p className="text-muted-foreground px-2 py-4 text-xs">Loading…</p>
        )}
        {!loading && sessions.length === 0 && (
          <p className="text-muted-foreground px-2 py-4 text-xs leading-relaxed">
            No saved chats yet. Send a message to start one.
          </p>
        )}
        <div className="space-y-0.5">
          {sessions.map((session) => (
            <SessionItem
              key={session.session_id}
              session={session}
              active={session.session_id === activeSessionId}
              onSelect={() => selectSession(session.session_id)}
              onDelete={() => void handleDelete(session.session_id)}
            />
          ))}
        </div>
      </div>
    </aside>
  );
}
