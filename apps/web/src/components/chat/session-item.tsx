'use client';

import { Button } from '@/components/ui/button';
import { formatRelativeTime } from '@/lib/format-relative-time';
import type { SessionSummary } from '@/lib/session-api';
import { cn } from '@/lib/utils';
import { Trash2 } from 'lucide-react';

type SessionItemProps = {
  session: SessionSummary;
  active: boolean;
  disabled?: boolean;
  onSelect: () => void;
  onDelete: () => void;
};

export function SessionItem({ session, active, disabled, onSelect, onDelete }: SessionItemProps) {
  const label = session.title?.trim() || 'New chat';
  return (
    <div
      className={cn(
        'group flex items-center gap-1 rounded-md px-2 py-1.5 text-sm transition-colors',
        active ? 'bg-sidebar-accent text-sidebar-accent-foreground' : 'hover:bg-sidebar-accent/60',
      )}
    >
      <button
        type="button"
        className="min-w-0 flex-1 text-left"
        onClick={onSelect}
        disabled={disabled}
      >
        <span className="block truncate font-medium">{label}</span>
        <span className="text-muted-foreground block truncate text-xs">
          {formatRelativeTime(session.updated_at)}
        </span>
      </button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-7 w-7 shrink-0 opacity-0 group-hover:opacity-100"
        disabled={disabled}
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        aria-label="Delete chat"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}
