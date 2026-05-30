import Link from 'next/link';
import { ThemeToggle } from './theme-toggle';
import { SITE } from '@/lib/constants';
import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export function Navbar() {
  return (
    <header className="border-border/40 bg-background/70 sticky top-0 z-50 w-full border-b backdrop-blur-xl">
      <div className="container mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-8">
          <Link href="/" className="font-heading text-lg font-semibold tracking-tight">
            {SITE.name}
          </Link>
          <nav className="hidden items-center gap-6 md:flex">
            <Link
              href="/demo"
              className="text-muted-foreground hover:text-primary text-sm font-medium transition-colors"
            >
              Demo
            </Link>
            <Link
              href="/docs"
              className="text-muted-foreground hover:text-primary text-sm font-medium transition-colors"
            >
              Docs
            </Link>
            <a
              href={SITE.dockerHub}
              target="_blank"
              rel="noreferrer"
              className="text-muted-foreground hover:text-primary text-sm font-medium transition-colors"
            >
              Docker
            </a>
            <a
              href={SITE.github}
              target="_blank"
              rel="noreferrer"
              className="text-muted-foreground hover:text-primary text-sm font-medium transition-colors"
            >
              GitHub
            </a>
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/docs/self-hosting"
            className={cn(buttonVariants({ size: 'sm' }), 'hidden sm:inline-flex')}
          >
            Run with Docker
          </Link>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
