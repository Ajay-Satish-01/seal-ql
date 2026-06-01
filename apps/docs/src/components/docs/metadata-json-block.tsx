import { CodeBlock } from '@/components/code-block';

interface MetadataJsonBlockProps {
  /** Pre-formatted JSON (hoist static strings at module level when possible). */
  code: string;
  title?: string;
  className?: string;
}

/** Renders a labeled JSON example block for metadata docs and demos. */
export function MetadataJsonBlock({ code, title, className }: MetadataJsonBlockProps) {
  return (
    <div className={className}>
      {title ? <p className="text-foreground mb-2 text-sm font-semibold">{title}</p> : null}
      <CodeBlock language="json" code={code} />
    </div>
  );
}
