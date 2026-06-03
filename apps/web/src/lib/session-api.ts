import { formatApiError } from '@/lib/api-error';
import { authHeaders, normalizeBaseUrl } from '@/lib/connection';

export interface SessionSummary {
  session_id: string;
  title: string | null;
  database_id: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface SessionMessage {
  role: string;
  content: string;
  created_at: string | null;
}

export interface SessionDetail {
  session_id: string;
  title: string | null;
  database_id: string | null;
  messages: SessionMessage[];
  created_at: string;
  updated_at: string;
}

async function readError(res: Response): Promise<never> {
  const detail = await res.text();
  throw new Error(formatApiError(res.status, detail));
}

export interface SessionListResult {
  sessions: SessionSummary[];
  has_more: boolean;
}

export async function listSessions(
  baseUrl: string,
  apiKey: string | undefined,
  databaseId?: string,
  options?: { limit?: number; offset?: number },
): Promise<SessionListResult> {
  const params = new URLSearchParams();
  if (databaseId) params.set('database_id', databaseId);
  if (options?.limit != null) params.set('limit', String(options.limit));
  if (options?.offset != null) params.set('offset', String(options.offset));
  const qs = params.toString();
  const url = `${normalizeBaseUrl(baseUrl)}/v1/chat/sessions${qs ? `?${qs}` : ''}`;
  const res = await fetch(url, {
    headers: { Accept: 'application/json', ...authHeaders(apiKey ?? '') },
  });
  if (!res.ok) await readError(res);
  const body = (await res.json()) as SessionListResult;
  return { sessions: body.sessions ?? [], has_more: body.has_more ?? false };
}

export async function getSession(
  baseUrl: string,
  sessionId: string,
  apiKey?: string,
): Promise<SessionDetail> {
  const encoded = encodeURIComponent(sessionId);
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/v1/chat/sessions/${encoded}`, {
    headers: { Accept: 'application/json', ...authHeaders(apiKey ?? '') },
  });
  if (!res.ok) await readError(res);
  return res.json() as Promise<SessionDetail>;
}

export async function deleteSession(
  baseUrl: string,
  sessionId: string,
  apiKey?: string,
): Promise<void> {
  const encoded = encodeURIComponent(sessionId);
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/v1/chat/sessions/${encoded}`, {
    method: 'DELETE',
    headers: { Accept: 'application/json', ...authHeaders(apiKey ?? '') },
  });
  if (!res.ok) await readError(res);
}
