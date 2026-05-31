import { formatApiError } from '@/lib/api-error';
import { authHeaders, normalizeBaseUrl } from '@/lib/connection';
import type { ChartSpec } from 'seal';

export type ConnectionProbeResult =
  | { ok: true; tableCount: number }
  | { ok: false; message: string };

/** Verify the API is reachable and the API key (if any) works for /v1/catalog. */
export async function probeApiConnection(
  baseUrl: string,
  apiKey: string,
  signal?: AbortSignal,
): Promise<ConnectionProbeResult> {
  const url = normalizeBaseUrl(baseUrl.trim());
  if (!url) {
    return { ok: false, message: 'API URL is required' };
  }

  try {
    const health = await fetch(`${url}/health`, { signal });
    if (!health.ok) {
      const detail = await health.text();
      return { ok: false, message: formatApiError(health.status, detail) };
    }

    const catalog = await fetch(`${url}/v1/catalog`, {
      headers: authHeaders(apiKey.trim()),
      signal,
    });
    if (!catalog.ok) {
      const detail = await catalog.text();
      return { ok: false, message: formatApiError(catalog.status, detail) };
    }

    const body = (await catalog.json()) as { tables?: unknown[] };
    const tableCount = Array.isArray(body.tables) ? body.tables.length : 0;
    return { ok: true, tableCount };
  } catch (error) {
    if ((error as Error).name === 'AbortError') {
      return { ok: false, message: 'Connection check cancelled' };
    }
    const message = error instanceof Error ? error.message : 'Could not reach API';
    return { ok: false, message };
  }
}

export interface QueryResponse {
  sql: string;
  columns: Array<{ name: string; type: string }>;
  results: Record<string, unknown>[];
  chart: ChartSpec | null;
  metadata?: Record<string, unknown>;
}

export interface CatalogTable {
  name: string;
  schema?: string;
  table_description?: string | null;
  view_description?: string | null;
}

export interface CatalogResponse {
  version: string;
  tables: CatalogTable[];
}

export interface WorkspaceSettingsResponse {
  settings: Record<string, unknown>;
  schema?: Array<{
    key: string;
    env_name: string;
    hot_reload: boolean;
    value_type: string;
    description: string;
    default: unknown;
    secret?: boolean;
  }>;
  hot_reload_applied?: string[];
  pending_apply?: string[];
  restart_required?: string[];
  storage?: {
    settings_read_source?: string;
    catalog_read_source?: string;
    write_target?: string;
  };
}

async function readError(res: Response): Promise<never> {
  const detail = await res.text();
  throw new Error(formatApiError(res.status, detail));
}

export async function postQuery(
  baseUrl: string,
  query: string,
  apiKey: string,
  signal?: AbortSignal,
): Promise<QueryResponse> {
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/v1/query`, {
    method: 'POST',
    headers: authHeaders(apiKey),
    body: JSON.stringify({ query }),
    signal,
  });
  if (!res.ok) await readError(res);
  return res.json() as Promise<QueryResponse>;
}

export async function getCatalog(
  baseUrl: string,
  apiKey: string,
  signal?: AbortSignal,
): Promise<CatalogResponse> {
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/v1/catalog`, {
    headers: authHeaders(apiKey),
    signal,
  });
  if (!res.ok) await readError(res);
  return res.json() as Promise<CatalogResponse>;
}

export async function patchCatalogDescriptions(
  baseUrl: string,
  apiKey: string,
  tables: Array<{
    name: string;
    schema?: string;
    table_description?: string | null;
    view_description?: string | null;
  }>,
): Promise<CatalogResponse> {
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/v1/catalog/descriptions`, {
    method: 'PATCH',
    headers: authHeaders(apiKey),
    body: JSON.stringify({ tables }),
  });
  if (!res.ok) await readError(res);
  return res.json() as Promise<CatalogResponse>;
}

export async function getWorkspaceSettings(
  baseUrl: string,
  apiKey: string,
): Promise<WorkspaceSettingsResponse> {
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/v1/workspace/settings`, {
    headers: authHeaders(apiKey),
  });
  if (!res.ok) await readError(res);
  return res.json() as Promise<WorkspaceSettingsResponse>;
}

export async function patchWorkspaceSettings(
  baseUrl: string,
  apiKey: string,
  settings: Record<string, unknown>,
): Promise<WorkspaceSettingsResponse> {
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/v1/workspace/settings`, {
    method: 'PATCH',
    headers: authHeaders(apiKey),
    body: JSON.stringify({ settings }),
  });
  if (!res.ok) await readError(res);
  return res.json() as Promise<WorkspaceSettingsResponse>;
}

export async function applyWorkspaceSettings(
  baseUrl: string,
  apiKey: string,
): Promise<WorkspaceSettingsResponse> {
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/v1/workspace/settings/apply`, {
    method: 'POST',
    headers: authHeaders(apiKey),
  });
  if (!res.ok) await readError(res);
  return res.json() as Promise<WorkspaceSettingsResponse>;
}

export async function syncCatalog(
  baseUrl: string,
  apiKey: string,
): Promise<{ added: number; updated: number; preserved: number; removed: number; path: string }> {
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/v1/catalog/sync`, {
    method: 'POST',
    headers: authHeaders(apiKey),
  });
  if (!res.ok) await readError(res);
  return res.json() as Promise<{
    added: number;
    updated: number;
    preserved: number;
    removed: number;
    path: string;
  }>;
}

export async function reindexVector(
  baseUrl: string,
  apiKey: string,
): Promise<{ status: string; indexed_tables: number }> {
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/v1/vector/reindex`, {
    method: 'POST',
    headers: authHeaders(apiKey),
  });
  if (!res.ok) await readError(res);
  return res.json() as Promise<{ status: string; indexed_tables: number }>;
}
