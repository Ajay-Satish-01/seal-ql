import { DocsSidebar } from '@/components/docs/docs-sidebar';

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="container mx-auto flex max-w-7xl flex-1 flex-col px-4 md:flex-row md:px-6">
      <aside className="border-border/40 w-full shrink-0 py-8 md:w-64 md:border-r md:py-0">
        <div className="docs-sidebar-scroll md:sticky md:top-16 md:z-20 md:max-h-[calc(100dvh-4rem)] md:overflow-y-auto md:overscroll-y-contain md:py-8 md:pr-8">
          <DocsSidebar />
        </div>
      </aside>
      <main className="min-w-0 flex-1 py-8 md:pl-12 xl:pl-16">{children}</main>
    </div>
  );
}
