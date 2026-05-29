import Link from 'next/link';
import { ScrollArea } from '@/components/ui/scroll-area';

const sidebarLinks = [
  { title: 'Introduction', href: '/docs' },
  { title: 'Quickstart', href: '/docs/quickstart' },
  { title: 'Python SDK', href: '/docs/python-sdk' },
  { title: 'TypeScript SDK', href: '/docs/typescript-sdk' },
  { title: 'Architecture', href: '/docs/architecture' },
];

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="container mx-auto flex max-w-7xl flex-1 flex-col px-4 md:flex-row md:px-6">
      <aside className="border-border/40 w-full flex-shrink-0 py-8 md:w-64 md:border-r md:pr-8">
        {/* We use standard nav element for simplicity rather than importing a heavy component */}
        <nav className="sticky top-24 flex flex-col gap-2">
          <h3 className="text-muted-foreground mb-2 text-sm font-semibold tracking-wider uppercase">
            Getting Started
          </h3>
          {sidebarLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="hover:text-primary hover:bg-secondary/50 -mx-3 rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
            >
              {link.title}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="min-w-0 flex-1 py-8 md:pl-12 xl:pl-16">{children}</main>
    </div>
  );
}
