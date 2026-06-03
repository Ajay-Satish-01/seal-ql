'use client';

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

type ChatSessionContextValue = {
  refreshKey: number;
  refreshSessions: () => void;
};

const ChatSessionContext = createContext<ChatSessionContextValue | null>(null);

export function ChatSessionProvider({ children }: { children: ReactNode }) {
  const [refreshKey, setRefreshKey] = useState(0);
  const refreshSessions = useCallback(() => setRefreshKey((k) => k + 1), []);
  const value = useMemo(
    () => ({ refreshKey, refreshSessions }),
    [refreshKey, refreshSessions],
  );
  return <ChatSessionContext.Provider value={value}>{children}</ChatSessionContext.Provider>;
}

export function useChatSessionList(): ChatSessionContextValue {
  const ctx = useContext(ChatSessionContext);
  if (!ctx) {
    throw new Error('useChatSessionList must be used within ChatSessionProvider');
  }
  return ctx;
}
