'use client';

import { SealLogo } from '@/components/seal-logo';
import { docsPageUrl } from '@/lib/docs-url';
import { cn } from '@/lib/utils';
import { Database, MessageSquare, Search, Settings, Sparkles, Table2 } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV = [
  { href: '/query', label: 'Query', icon: Search },
  { href: '/chat', label: 'Chat', icon: MessageSquare },
  { href: '/schema', label: 'Schema', icon: Table2 },
  { href: '/catalog', label: 'Catalog', icon: Database },
  { href: '/settings', label: 'Settings', icon: Settings },
  { href: '/vector', label: 'Vector', icon: Sparkles },
] as const;

export function DashboardSidebar() {
  const pathname = usePathname();

  return (
    <aside className="border-border bg-sidebar/95 text-sidebar-foreground flex w-56 shrink-0 flex-col border-r backdrop-blur-md">
      <div className="border-border flex items-center gap-2 border-b px-4 py-4">
        <SealLogo className="text-primary h-7 w-7" />
        <span className="font-heading text-sm font-semibold tracking-tight">Seal Console</span>
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-2">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors',
                active
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                  : 'hover:bg-sidebar-accent/60',
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="text-muted-foreground space-y-1 px-4 py-3 text-xs leading-relaxed">
        <p>Live API · port 3001</p>
        <p className="flex flex-wrap gap-x-2 gap-y-0.5">
          <a
            href={docsPageUrl('/docs/embedding')}
            target="_blank"
            rel="noreferrer"
            className="text-primary hover:underline"
          >
            Embedding guide
          </a>
          <span aria-hidden className="text-border">
            ·
          </span>
          <a
            href={docsPageUrl('/docs/local-evals')}
            target="_blank"
            rel="noreferrer"
            className="text-primary hover:underline"
          >
            Local evals
          </a>
        </p>
      </div>
    </aside>
  );
}
