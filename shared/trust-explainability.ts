/**
 * Trust / explainability feature flag resolution for dashboard + docs.
 * API truth comes from GET /health; frontends may set NEXT_PUBLIC_SEAL_TRUST_EXPLAINABILITY_ENABLED.
 */

import type { ChatMetadata, ExecutionMetadata } from './metadata-contract';
import { hasMetadataContent } from './metadata-contract';

export interface TrustCapabilities {
  trust_explainability_enabled?: boolean;
}

export interface TrustSurfaceInput {
  sql?: string | null;
  sources?: readonly string[] | null;
  metadata?: ChatMetadata | ExecutionMetadata | null;
}

const TRUTHY = new Set(['1', 'true', 'yes', 'on']);

export function parseTrustExplainabilityFlag(value: unknown): boolean | undefined {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase();
    if (TRUTHY.has(normalized)) return true;
    if (normalized === 'false' || normalized === '0' || normalized === 'no' || normalized === 'off') {
      return false;
    }
  }
  return undefined;
}

/** Read build-time / runtime public env (Next.js inlines at build). */
export function readTrustExplainabilityFromEnv(): boolean {
  const raw =
    typeof process !== 'undefined'
      ? process.env.NEXT_PUBLIC_SEAL_TRUST_EXPLAINABILITY_ENABLED
      : undefined;
  return parseTrustExplainabilityFlag(raw) ?? false;
}

/** Prefer API health capabilities; fall back to public env when unknown. */
export function resolveTrustExplainabilityEnabled(
  capabilities?: TrustCapabilities | null,
): boolean {
  const fromApi = parseTrustExplainabilityFlag(capabilities?.trust_explainability_enabled);
  if (fromApi !== undefined) return fromApi;
  return readTrustExplainabilityFromEnv();
}

export function hasTrustSurfaceContent(input: TrustSurfaceInput): boolean {
  if (typeof input.sql === 'string' && input.sql.length > 0) return true;
  if (input.sources && input.sources.length > 0) return true;
  const meta = input.metadata;
  if (!meta) return false;
  if (meta.tables_used && meta.tables_used.length > 0) return true;
  if (meta.columns_used && meta.columns_used.length > 0) return true;
  if (meta.catalog_matches && meta.catalog_matches.length > 0) return true;
  const chatMeta = meta as ChatMetadata;
  if (chatMeta.scope) return true;
  if (typeof meta.repair_attempts === 'number' && meta.repair_attempts > 0) return true;
  if (chatMeta.refusal) return true;
  if (chatMeta.suggested_queries && chatMeta.suggested_queries.length > 0) return true;
  return false;
}

export function shouldShowTrustPanel(
  trustEnabled: boolean,
  input: TrustSurfaceInput,
): boolean {
  if (!trustEnabled) return false;
  return hasTrustSurfaceContent(input) || hasMetadataContent(input.metadata ?? undefined);
}
