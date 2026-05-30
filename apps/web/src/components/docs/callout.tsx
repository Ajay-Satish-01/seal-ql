import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { Info, AlertTriangle, CheckCircle2 } from 'lucide-react';

type CalloutVariant = 'info' | 'warning' | 'success';

const styles: Record<CalloutVariant, string> = {
  info: 'border-teal-500/40 bg-teal-500/5 text-foreground',
  warning: 'border-amber-500/50 bg-amber-500/5 text-foreground',
  success: 'border-primary/40 bg-primary/5 text-foreground',
};

const icons: Record<CalloutVariant, ReactNode> = {
  info: <Info className="h-5 w-5 shrink-0 text-teal-600 dark:text-teal-400" />,
  warning: <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />,
  success: <CheckCircle2 className="text-primary h-5 w-5 shrink-0" />,
};

interface CalloutProps {
  variant?: CalloutVariant;
  title?: string;
  children: ReactNode;
  className?: string;
}

export function Callout({ variant = 'info', title, children, className }: CalloutProps) {
  return (
    <div className={cn('my-6 flex gap-3 rounded-lg border p-4', styles[variant], className)}>
      {icons[variant]}
      <div className="min-w-0 text-sm leading-relaxed">
        {title ? <p className="mb-1 font-semibold">{title}</p> : null}
        <div className="text-muted-foreground [&_strong]:text-foreground">{children}</div>
      </div>
    </div>
  );
}
