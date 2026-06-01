import type { MetadataFieldDef } from '@/lib/execution-metadata';

interface MetadataFieldListProps {
  fields: MetadataFieldDef[];
  className?: string;
}

export function MetadataFieldList({ fields, className }: MetadataFieldListProps) {
  return (
    <ul
      className={
        className ??
        'text-muted-foreground mt-4 list-disc space-y-2 pl-6 text-sm'
      }
    >
      {fields.map((field) => (
        <li key={field.name}>
          <code>{field.name}</code>
          {' — '}
          {field.description}
        </li>
      ))}
    </ul>
  );
}
