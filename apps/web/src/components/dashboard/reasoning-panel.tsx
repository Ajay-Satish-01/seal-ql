'use client';

import { Card } from '@/components/ui/card';
import type { ReasoningMetadata } from '@seal/metadata-contract';
import { cn } from '@/lib/utils';

interface ReasoningPanelProps {
  reasoning?: ReasoningMetadata | null;
  className?: string;
}

function Section({
  title,
  items,
  variant = 'default',
}: {
  title: string;
  items: string[];
  variant?: 'default' | 'warning';
}) {
  if (!items.length) return null;
  return (
    <div className="space-y-1.5">
      <p
        className={cn(
          'text-xs font-medium tracking-wide uppercase',
          variant === 'warning' ? 'text-amber-700 dark:text-amber-400' : 'text-muted-foreground',
        )}
      >
        {title}
      </p>
      <ul className="text-sm leading-relaxed">
        {items.map((item, idx) => (
          <li key={`${title}-${idx}`} className="list-inside list-disc">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ReasoningPanel({ reasoning, className }: ReasoningPanelProps) {
  if (!reasoning) return null;

  const hasContent =
    reasoning.clarification_required ||
    (reasoning.inferred_context?.length ?? 0) > 0 ||
    (reasoning.clarifying_questions?.length ?? 0) > 0 ||
    (reasoning.analysis_followups?.length ?? 0) > 0 ||
    (reasoning.research_notes?.length ?? 0) > 0;

  if (!hasContent) return null;

  return (
    <Card className={cn('border-border/60 bg-muted/10 space-y-3 p-3', className)}>
      <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
        Reasoning layers
      </p>
      <Section title="Context from conversation" items={reasoning.inferred_context ?? []} />
      <Section
        title={reasoning.clarification_required ? 'Details needed' : 'Clarifying questions'}
        items={reasoning.clarifying_questions ?? []}
        variant={reasoning.clarification_required ? 'warning' : 'default'}
      />
      <Section title="Research notes" items={reasoning.research_notes ?? []} />
      <Section title="Suggested follow-ups" items={reasoning.analysis_followups ?? []} />
    </Card>
  );
}
