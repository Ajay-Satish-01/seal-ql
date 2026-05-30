import Link from 'next/link';

const sidebarGroups = [
  {
    title: 'Overview',
    links: [
      { title: 'Introduction', href: '/docs' },
      { title: 'Features', href: '/docs/features' },
      { title: 'Architecture', href: '/docs/architecture' },
    ],
  },
  {
    title: 'Getting Started',
    links: [
      { title: 'Quickstart', href: '/docs/quickstart' },
      { title: 'Integration Guide', href: '/docs/integration-guide' },
      { title: 'Self-Hosting', href: '/docs/self-hosting' },
    ],
  },
  {
    title: 'Integration',
    links: [
      { title: 'API Reference', href: '/docs/api-reference' },
      { title: 'Python SDK', href: '/docs/python-sdk' },
      { title: 'TypeScript SDK', href: '/docs/typescript-sdk' },
      { title: 'Charts & Analysis', href: '/docs/charts-analysis' },
    ],
  },
  {
    title: 'Examples',
    links: [{ title: 'Interactive Demo', href: '/demo' }],
  },
];

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="container mx-auto flex max-w-7xl flex-1 flex-col px-4 md:flex-row md:px-6">
      <aside className="border-border/40 w-full flex-shrink-0 py-8 md:w-64 md:border-r md:pr-8">
        <nav className="sticky top-24 flex flex-col gap-6">
          {sidebarGroups.map((group) => (
            <div key={group.title} className="flex flex-col gap-2">
              <h3 className="text-muted-foreground mb-1 text-xs font-semibold tracking-wider uppercase">
                {group.title}
              </h3>
              {group.links.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="hover:text-primary hover:bg-secondary/50 -mx-3 rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
                >
                  {link.title}
                </Link>
              ))}
            </div>
          ))}
        </nav>
      </aside>
      <main className="min-w-0 flex-1 py-8 md:pl-12 xl:pl-16">{children}</main>
    </div>
  );
}
