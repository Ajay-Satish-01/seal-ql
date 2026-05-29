import Link from 'next/link';
import { ThemeToggle } from './theme-toggle';

export function Navbar() {
  return (
    <header className="border-border/40 bg-background/60 sticky top-0 z-50 w-full border-b backdrop-blur-xl">
      <div className="container mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center space-x-2">
            <span className="from-primary bg-gradient-to-r to-blue-400 bg-clip-text text-xl font-bold text-transparent">
              Intelligence Connector
            </span>
          </Link>
          <nav className="hidden gap-6 md:flex">
            <Link
              href="/docs"
              className="text-muted-foreground hover:text-foreground text-sm font-medium transition-colors"
            >
              Documentation
            </Link>
            <a
              href="https://github.com/your-org/intelligence_connector"
              target="_blank"
              rel="noreferrer"
              className="text-muted-foreground hover:text-foreground text-sm font-medium transition-colors"
            >
              GitHub
            </a>
          </nav>
        </div>
        <div className="flex items-center space-x-4">
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
