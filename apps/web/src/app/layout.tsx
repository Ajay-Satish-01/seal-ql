import type { Metadata } from 'next';
import { Fraunces, IBM_Plex_Mono, IBM_Plex_Sans } from 'next/font/google';
import { ConnectionBar } from '@/components/dashboard/connection-bar';
import { DashboardSidebar } from '@/components/dashboard/sidebar';
import { Toaster } from '@/components/ui/sonner';
import { ThemeProvider } from '@/components/theme-provider';
import { ThemeToggle } from '@/components/theme-toggle';
import { ConnectionProvider } from '@/contexts/connection-context';
import './globals.css';

const plexSans = IBM_Plex_Sans({
  variable: '--font-plex-sans',
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  display: 'swap',
});

const plexMono = IBM_Plex_Mono({
  variable: '--font-plex-mono',
  subsets: ['latin'],
  weight: ['400', '500'],
  display: 'swap',
});

const fraunces = Fraunces({
  variable: '--font-fraunces',
  subsets: ['latin'],
  weight: ['500', '600', '700'],
  display: 'swap',
});

export const metadata: Metadata = {
  title: { default: 'Seal Console', template: '%s · Seal Console' },
  description: 'Operational dashboard for a running Seal API.',
  icons: { icon: [{ url: '/seal-logo.svg', type: 'image/svg+xml' }] },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${plexSans.variable} ${plexMono.variable} ${fraunces.variable} h-full antialiased`}
    >
      <body className="bg-background text-foreground console-shell flex h-full min-h-screen font-sans">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          <ConnectionProvider>
            <DashboardSidebar />
            <div className="flex min-w-0 flex-1 flex-col">
              <header className="border-border flex items-center justify-between border-b px-4 py-2.5">
                <span className="text-primary text-xs font-semibold tracking-[0.2em] uppercase">
                  Command center
                </span>
                <ThemeToggle />
              </header>
              <ConnectionBar />
              <main className="flex-1 overflow-auto p-6">{children}</main>
            </div>
          </ConnectionProvider>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
