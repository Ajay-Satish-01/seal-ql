/**
 * Human-readable labels for execution metadata (dashboard + docs demo).
 */

import type { ChatMetadata, EnhancementMetadata, ExecutionMetadata } from './metadata-contract';

export interface MetadataBadge {
  label: string;
  variant: 'default' | 'warning' | 'destructive' | 'muted';
}

export function metadataBadges(meta: ChatMetadata | ExecutionMetadata): MetadataBadge[] {
  const badges: MetadataBadge[] = [];

  if (meta.database_id) {
    badges.push({ label: `db: ${meta.database_id}`, variant: 'muted' });
  }
  if (typeof meta.row_count === 'number') {
    badges.push({ label: `${meta.row_count} row(s)`, variant: 'default' });
  }
  if (typeof meta.execution_time_ms === 'number') {
    badges.push({ label: `${meta.execution_time_ms.toFixed(1)} ms`, variant: 'muted' });
  }
  if (meta.truncated) {
    badges.push({ label: 'truncated', variant: 'warning' });
  }
  if (meta.used_sql === true) {
    badges.push({ label: 'used_sql', variant: 'default' });
  } else if (meta.used_sql === false) {
    badges.push({ label: 'no sql', variant: 'muted' });
  }

  const chatMeta = meta as ChatMetadata;
  if (chatMeta.refusal) {
    badges.push({ label: 'refusal', variant: 'destructive' });
  }
  if (chatMeta.sql_error) {
    badges.push({ label: 'sql_error', variant: 'destructive' });
  }
  if (chatMeta.scope && !chatMeta.scope.in_scope) {
    badges.push({ label: `scope: ${chatMeta.scope.reason}`, variant: 'warning' });
  }

  const enh = meta.enhancement;
  if (enh) {
    badges.push(...enhancementBadges(enh));
  }

  return badges;
}

function enhancementBadges(enh: EnhancementMetadata): MetadataBadge[] {
  const badges: MetadataBadge[] = [];
  if (enh.enabled) {
    const applied =
      enh.applied.length > 0 ? enh.applied.join(', ') : 'none';
    badges.push({ label: `enhancement: ${applied}`, variant: 'default' });
  }
  if (enh.vector_skipped_reason) {
    badges.push({ label: `vector: ${enh.vector_skipped_reason}`, variant: 'warning' });
  }
  if (enh.unavailable_reason) {
    badges.push({ label: enh.unavailable_reason, variant: 'warning' });
  }
  return badges;
}
