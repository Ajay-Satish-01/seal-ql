export {
  type ChatMetadata,
  type ChatStreamMeta,
  type ColumnDescriptor,
  type EnhancementMetadata,
  type ExecutionMetadata,
  type ScopeMetadata,
  formatMetadataJson,
  hasMetadataContent,
} from '@seal/metadata-contract';

/** `POST /v1/query` response `metadata` (execution fields only). */
export type { ExecutionMetadata as QueryMetadata } from '@seal/metadata-contract';
