import { cn } from '@/lib/utils';

export interface ConfigRow {
  name: string;
  type: string;
  /** Typical or documented default — shown for quick scanning. */
  default?: string;
  /** What the setting controls and when you would change it. */
  description: string;
  /** Observable behavior after startup, a request, or a settings apply. */
  expect: string;
}

interface ConfigReferenceProps {
  rows: ConfigRow[];
  className?: string;
}

/**
 * Environment and workspace settings table with an explicit “what to expect” column
 * so reference pages read like product docs, not a flat variable list.
 */
export function ConfigReference({ rows, className }: ConfigReferenceProps) {
  return (
    <div
      className={cn(
        'not-prose border-border/50 my-8 overflow-x-auto rounded-xl border text-sm',
        className,
      )}
    >
      <table className="w-full min-w-[40rem] text-left">
        <thead>
          <tr className="border-border/50 bg-muted/40 border-b">
            <th className="text-foreground px-4 py-3 font-semibold">Variable</th>
            <th className="text-foreground px-4 py-3 font-semibold">Type</th>
            <th className="text-foreground hidden px-4 py-3 font-semibold sm:table-cell">
              Default
            </th>
            <th className="text-foreground px-4 py-3 font-semibold">Purpose</th>
            <th className="text-foreground px-4 py-3 font-semibold">What to expect</th>
          </tr>
        </thead>
        <tbody className="text-muted-foreground divide-border/40 divide-y">
          {rows.map((row) => (
            <tr key={row.name}>
              <td className="text-foreground px-4 py-3 align-top font-mono text-xs">{row.name}</td>
              <td className="px-4 py-3 align-top font-mono text-xs">{row.type}</td>
              <td className="hidden px-4 py-3 align-top font-mono text-xs sm:table-cell">
                {row.default ?? '—'}
              </td>
              <td className="px-4 py-3 align-top leading-relaxed">{row.description}</td>
              <td className="px-4 py-3 align-top leading-relaxed">{row.expect}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface ConfigSectionProps {
  id?: string;
  title: string;
  intro: React.ReactNode;
  children?: React.ReactNode;
  rows?: ConfigRow[];
}

/** Section heading plus narrative intro and optional settings table. */
export function ConfigSection({ id, title, intro, children, rows }: ConfigSectionProps) {
  return (
    <section id={id} className="scroll-mt-24">
      <h2 className="text-foreground mt-12 text-2xl font-bold first:mt-0">{title}</h2>
      <div className="text-muted-foreground mt-4 space-y-4 leading-relaxed">{intro}</div>
      {rows ? <ConfigReference rows={rows} /> : null}
      {children}
    </section>
  );
}
