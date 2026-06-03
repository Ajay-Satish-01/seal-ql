'use client';

import { SessionSidebar } from '@/components/chat/session-sidebar';
import { ChatSessionProvider } from '@/contexts/chat-session-context';
import { Suspense, type ReactNode } from 'react';

function ChatLayoutInner({ children }: { children: ReactNode }) {
  return (
    <div className="-mx-6 -mb-6 flex min-h-[calc(100vh-8rem)] flex-1">
      <Suspense fallback={<aside className="border-border w-56 shrink-0 border-r" />}>
        <SessionSidebar />
      </Suspense>
      <div className="min-w-0 flex-1 overflow-auto p-6">{children}</div>
    </div>
  );
}

export default function ChatLayout({ children }: { children: ReactNode }) {
  return (
    <ChatSessionProvider>
      <ChatLayoutInner>{children}</ChatLayoutInner>
    </ChatSessionProvider>
  );
}
