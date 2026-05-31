'use client';

import { Badge } from '@/components/ui/badge';
import { demoPresets } from '@/lib/demo-fixtures';
import { cn } from '@/lib/utils';
import { CheckCircle2 } from 'lucide-react';

const PIPELINE = ['Plan', 'Validate', 'Execute', 'Chart'] as const;

interface QueryConsoleProps {
  selectedId: string;
  onSelect: (id: string) => void;
  query: string;
}

export function QueryConsole({ selectedId, onSelect, query }: QueryConsoleProps) {
  return (
    <div className="space-y-6">
      <div>
        <label
          htmlFor="preset-select"
          className="text-muted-foreground mb-2 block text-xs font-medium tracking-wider uppercase"
        >
          Example query
        </label>
        <select
          id="preset-select"
          value={selectedId}
          onChange={(e) => onSelect(e.target.value)}
          className="border-input bg-background w-full rounded-md border px-3 py-2 text-sm"
        >
          {demoPresets.map((p) => (
            <option key={p.id} value={p.id}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      <div className="border-border/50 bg-card/50 rounded-lg border p-4">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="text-muted-foreground text-xs font-medium uppercase">
            Natural language
          </span>
          <Badge variant="outline" className="text-xs">
            Simulated
          </Badge>
        </div>
        <p className="text-sm leading-relaxed">&ldquo;{query}&rdquo;</p>
      </div>

      <div>
        <p className="text-muted-foreground mb-3 text-xs font-medium tracking-wider uppercase">
          Pipeline
        </p>
        <ol className="space-y-2">
          {PIPELINE.map((step, i) => (
            <li
              key={step}
              className={cn(
                'flex items-center gap-2 rounded-md px-2 py-1.5 text-sm',
                i === PIPELINE.length - 1
                  ? 'bg-primary/10 text-foreground'
                  : 'text-muted-foreground',
              )}
            >
              <CheckCircle2 className="text-primary h-4 w-4 shrink-0" />
              {step}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
