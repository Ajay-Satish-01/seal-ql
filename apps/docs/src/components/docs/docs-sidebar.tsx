'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

const sidebarGroups = [
  {
    title: 'Overview',
    links: [
      { title: 'Introduction', href: '/docs' },
      { title: 'Features', href: '/docs/features' },
      { title: 'Architecture', href: '/docs/architecture' },
      { title: 'How it works', href: '/docs/how-it-works' },
    ],
  },
  {
    title: 'Getting Started',
    links: [
      { title: 'Quickstart', href: '/docs/quickstart' },
      { title: 'Integration guide', href: '/docs/integration-guide' },
      { title: 'Embedding Seal', href: '/docs/embedding' },
      { title: 'Self-hosting (Docker)', href: '/docs/self-hosting' },
      { title: 'Authentication', href: '/docs/authentication' },
      { title: 'Dashboard (port 3001)', href: '/docs/dashboard' },
    ],
  },
  {
    title: 'Configuration',
    links: [
      { title: 'Configuration reference', href: '/docs/configuration' },
      { title: 'Multi-database routing', href: '/docs/multi-database' },
      { title: 'Workspace settings', href: '/docs/workspace' },
      { title: 'Data catalog', href: '/docs/data-catalog' },
      { title: 'Guardrails', href: '/docs/guardrails' },
      { title: 'Zero-trust SQL', href: '/docs/zero-trust-sql' },
      { title: 'Prompt enhancement', href: '/docs/prompt-enhancement' },
      { title: 'Vector RAG', href: '/docs/vector-rag' },
    ],
  },
  {
    title: 'Chat & Query',
    links: [
      { title: 'Chat & Q&A', href: '/docs/chat-qa' },
      { title: 'Trust & explainability', href: '/docs/trust-explainability' },
      { title: 'Execution metadata', href: '/docs/execution-metadata' },
      { title: 'SSE streaming', href: '/docs/chat-streaming' },
      { title: 'Charts & analysis', href: '/docs/charts-analysis' },
      { title: 'Agent frameworks', href: '/docs/agent-frameworks' },
    ],
  },
  {
    title: 'API & SDKs',
    links: [
      { title: 'API reference', href: '/docs/api-reference' },
      { title: 'Python SDK', href: '/docs/python-sdk' },
      { title: 'TypeScript SDK', href: '/docs/typescript-sdk' },
    ],
  },
  {
    title: 'Quality & Contributing',
    links: [
      { title: 'Testing & CI', href: '/docs/testing' },
      { title: 'Local planner evals', href: '/docs/local-evals' },
      { title: 'Contributing', href: '/docs/contributing' },
      { title: 'Interactive demo', href: '/demo' },
    ],
  },
] as const;

export function DocsSidebar() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-6" aria-label="Documentation">
      {sidebarGroups.map((group) => (
        <div key={group.title} className="flex flex-col gap-0.5">
          <h3 className="text-muted-foreground mb-1.5 px-2.5 text-xs font-semibold tracking-wider uppercase">
            {group.title}
          </h3>
          {group.links.map((link) => {
            const active =
              pathname === link.href ||
              (link.href !== '/docs' && pathname.startsWith(`${link.href}/`));
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'block rounded-r-md border-l-[3px] py-1.5 pr-3 pl-2.5 text-sm font-medium transition-colors',
                  active
                    ? 'border-primary bg-muted text-foreground font-semibold shadow-sm dark:bg-primary/25 dark:text-primary dark:shadow-[inset_0_0_0_1px_oklch(0.78_0.14_75/0.35)]'
                    : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground border-transparent',
                )}
              >
                {link.title}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
