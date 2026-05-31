import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface EndpointBlockProps {
  method: string;
  path: string;
  summary?: string;
  description?: string;
  children?: React.ReactNode;
}

const methodColors: Record<string, string> = {
  GET: 'bg-teal-500/15 text-teal-800 dark:text-teal-300',
  POST: 'bg-amber-500/15 text-amber-900 dark:text-amber-200',
  PUT: 'bg-blue-500/15 text-blue-800 dark:text-blue-300',
  DELETE: 'bg-red-500/15 text-red-800 dark:text-red-300',
};

export function EndpointBlock({
  method,
  path,
  summary,
  description,
  children,
}: EndpointBlockProps) {
  return (
    <section className="border-border/50 mb-10 border-b pb-10 last:border-0">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Badge className={cn('font-mono text-xs uppercase', methodColors[method] ?? '')}>
          {method}
        </Badge>
        <code className="font-mono text-sm font-medium">{path}</code>
      </div>
      {summary ? <h3 className="text-foreground mb-2 text-xl font-semibold">{summary}</h3> : null}
      {description ? (
        <p className="text-muted-foreground mb-4 leading-relaxed">{description}</p>
      ) : null}
      {children}
    </section>
  );
}
