import Link from 'next/link';
import { CheckCircle2 } from 'lucide-react';

export type SetupStep = {
  title: string;
  body: React.ReactNode;
  code?: string;
};

export function SetupChecklist({ steps }: { steps: SetupStep[] }) {
  return (
    <ol className="not-prose mt-8 space-y-8">
      {steps.map((step, index) => (
        <li key={step.title} className="relative flex gap-4">
          <div
            className="bg-primary/15 text-primary ring-primary/25 flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold ring-1"
            aria-hidden
          >
            {index + 1}
          </div>
          <div className="min-w-0 flex-1 pt-0.5">
            <h3 className="text-foreground mb-2 text-lg font-semibold">{step.title}</h3>
            <div className="text-muted-foreground space-y-3 text-sm leading-relaxed">{step.body}</div>
            {step.code ? (
              <pre className="mt-3 overflow-x-auto rounded-lg border border-border/50 bg-muted/40 p-4 font-mono text-xs text-foreground">
                {step.code}
              </pre>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}

export function SetupDoneBanner() {
  return (
    <div className="not-prose border-primary/30 bg-primary/5 mt-10 flex gap-3 rounded-xl border p-4">
      <CheckCircle2 className="text-primary mt-0.5 h-5 w-5 shrink-0" />
      <p className="text-muted-foreground text-sm leading-relaxed">
        <strong className="text-foreground">You are ready.</strong> Open the{' '}
        <Link href="/demo" className="text-primary hover:underline">
          interactive demo
        </Link>
        , the{' '}
        <Link href="/docs/dashboard" className="text-primary hover:underline">
          dashboard
        </Link>{' '}
        (port 3001), or integrate with the{' '}
        <Link href="/docs/python-sdk" className="text-primary hover:underline">
          SDKs
        </Link>
        .
      </p>
    </div>
  );
}
