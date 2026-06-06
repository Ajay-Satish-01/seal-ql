import type { CatalogTable } from '@/lib/seal-api';

const VIEW_KINDS = new Set(['view', 'materialized_view', 'continuous_aggregate']);

export function catalogEntryKey(table: CatalogTable): string {
  return `${table.schema ?? 'public'}.${table.name}`;
}

export function catalogUsesViewDescription(kind?: string | null): boolean {
  return kind != null && VIEW_KINDS.has(kind);
}

export function descriptionForEntry(table: CatalogTable): string {
  if (catalogUsesViewDescription(table.kind)) {
    return table.view_description ?? '';
  }
  return table.table_description ?? '';
}

export function descriptionLabelForEntry(table: CatalogTable): string {
  return catalogUsesViewDescription(table.kind) ? 'View description' : 'Table description';
}

export function snapshotDescriptions(tables: CatalogTable[]): Record<string, string> {
  const snap: Record<string, string> = {};
  for (const table of tables) {
    snap[catalogEntryKey(table)] = descriptionForEntry(table);
  }
  return snap;
}

export function snapshotsEqual(a: Record<string, string>, b: Record<string, string>): boolean {
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  for (const key of keys) {
    if ((a[key] ?? '') !== (b[key] ?? '')) return false;
  }
  return true;
}

export function patchPayloadForEntry(
  table: CatalogTable,
  description: string,
): {
  name: string;
  schema: string;
  table_description?: string;
  view_description?: string;
} {
  const base = {
    name: table.name,
    schema: table.schema ?? 'public',
  };
  if (catalogUsesViewDescription(table.kind)) {
    return { ...base, view_description: description };
  }
  return { ...base, table_description: description };
}

export function withDescription(table: CatalogTable, description: string): CatalogTable {
  if (catalogUsesViewDescription(table.kind)) {
    return { ...table, view_description: description };
  }
  return { ...table, table_description: description };
}
