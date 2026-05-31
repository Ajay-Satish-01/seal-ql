import { cn } from '@/lib/utils';

/** Consistent typography wrapper for documentation pages. */
export function DocsProse({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed',
        'prose-headings:font-heading prose-headings:text-foreground prose-h2:scroll-mt-24 prose-h3:scroll-mt-24',
        'prose-a:text-primary prose-a:underline-offset-4 hover:prose-a:underline',
        'prose-code:text-foreground prose-code:before:content-none prose-code:after:content-none',
        'prose-pre:bg-transparent prose-pre:p-0',
        className,
      )}
    >
      {children}
    </div>
  );
}
