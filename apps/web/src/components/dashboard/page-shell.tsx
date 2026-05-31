import type { ReactNode } from 'react';

interface PageShellProps {
  title: string;
  description: string;
  children: ReactNode;
  actions?: ReactNode;
}

export function PageShell({ title, description, children, actions }: PageShellProps) {
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="text-muted-foreground mt-1 max-w-2xl text-sm">{description}</p>
        </div>
        {actions}
      </div>
      {children}
    </div>
  );
}
