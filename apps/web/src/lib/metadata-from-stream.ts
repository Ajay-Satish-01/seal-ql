import type { ChatMetadata, ChatStreamMeta } from '@seal/metadata-contract';
import { hasMetadataContent, STREAM_META_METADATA_KEYS } from '@seal/metadata-contract';

/** Chat JSON `metadata` fields from a flat `seal.meta` SSE payload. */
export function chatMetadataFromStreamMeta(meta: ChatStreamMeta): ChatMetadata {
  const nested: Record<string, unknown> = { ...meta };
  delete nested.session_id;
  delete nested.sources;
  delete nested.sql;
  delete nested.results;
  delete nested.columns;
  delete nested.chart;
  return nested as ChatMetadata;
}

/** Build chat metadata from a partial seal.meta (e.g. after client validation soft-fail). */
export function chatMetadataFromPartial(partial: Partial<ChatStreamMeta>): ChatMetadata | null {
  const meta: ChatMetadata = {};
  const record = partial as Record<string, unknown>;
  for (const key of STREAM_META_METADATA_KEYS) {
    const value = record[key];
    if (value !== undefined && value !== null) {
      (meta as Record<string, unknown>)[key] = value;
    }
  }
  return hasMetadataContent(meta) ? meta : null;
}
