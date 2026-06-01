'use client';

import { MetadataJsonBlock } from '@/components/docs/metadata-json-block';
import { formatMetadataJson, hasMetadataContent, type ChatMetadata } from '@/lib/execution-metadata';

interface MetadataJsonPreviewProps {
  label?: string;
  metadata?: ChatMetadata;
}

export function MetadataJsonPreview({ label = 'metadata', metadata }: MetadataJsonPreviewProps) {
  if (!hasMetadataContent(metadata)) return null;

  return <MetadataJsonBlock title={label} code={formatMetadataJson(metadata)} />;
}
