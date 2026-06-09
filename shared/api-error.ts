/**
 * API error formatting for dashboard, docs, and SDK vendor copies.
 * Rate-limit markers: config/rate_limit_markers.json (synced on SDK prebuild).
 */
import rateLimitConfig from '../config/rate_limit_markers.json';

/** User-facing toast when the LLM provider throttles (HTTP 503 detail or rate-limit keywords). */
export const RATE_LIMIT_USER_MESSAGE = rateLimitConfig.user_message;

/** Substring markers for provider throttling (keep in sync via config/rate_limit_markers.json). */
export const RATE_LIMIT_MARKERS: readonly string[] = rateLimitConfig.markers;

/** Structured FastAPI error detail (session mismatch, guardrails, etc.). */
export type ApiErrorDetailObject = {
  code?: string;
  message?: string;
  detail?: string;
  reason?: string;
  suggested_queries?: string[];
  session_id?: string;
  pinned_database_id?: string;
  requested_database_id?: string;
};

function formatQueryOutOfScope(obj: ApiErrorDetailObject): string {
  const reason = obj.reason?.trim();
  const suggestions = Array.isArray(obj.suggested_queries)
    ? obj.suggested_queries.filter((q) => typeof q === 'string' && q.trim())
    : [];
  const reasonSuffix = reason ? ` (${reason})` : '';
  const hint =
    suggestions.length > 0
      ? `\n\nTry: ${suggestions.map((q) => `"${q}"`).join(' · ')}`
      : '';
  return `Query out of scope${reasonSuffix}.${hint}`;
}

function formatStructuredDetail(obj: ApiErrorDetailObject): string | undefined {
  if (obj.message) return obj.message;
  if (obj.code === 'session_database_id_mismatch') {
    return (
      `Session is pinned to database "${obj.pinned_database_id ?? '?'}" ` +
      `but request used "${obj.requested_database_id ?? '?'}". ` +
      'Start a new chat session or select the pinned database.'
    );
  }
  if (obj.detail === 'query_out_of_scope') {
    return formatQueryOutOfScope(obj);
  }
  if (obj.code) return obj.code;
  return undefined;
}

/** True when free-text indicates provider throttling. */
export function looksLikeRateLimitText(text: string): boolean {
  const lower = text.toLowerCase();
  return RATE_LIMIT_MARKERS.some((marker) => lower.includes(marker));
}

/** True when an HTTP status or message body indicates LLM rate limiting. */
export function isRateLimitSignal(status: number, text: string): boolean {
  if (looksLikeRateLimitText(text)) return true;
  // Seal maps provider throttling to HTTP 503 with a string detail (or empty body).
  return status === 503 && !text.trim();
}

/** Map thrown client errors (including fetch failures) to a user-visible message. */
export function formatClientError(error: unknown, fallback: string): string {
  if (error instanceof Error) {
    if (isRateLimitSignal(0, error.message)) return RATE_LIMIT_USER_MESSAGE;
    if (error.message.trim()) return error.message;
  }
  return fallback;
}

/** Extract a human-readable message from Seal API error responses. */
export function formatApiError(status: number, bodyText: string): string {
  const trimmed = bodyText.trim();
  if (!trimmed) {
    return isRateLimitSignal(status, '') ? RATE_LIMIT_USER_MESSAGE : `Request failed (${status})`;
  }

  if (isRateLimitSignal(status, trimmed)) {
    return RATE_LIMIT_USER_MESSAGE;
  }

  try {
    const json = JSON.parse(trimmed) as { detail?: unknown };
    if (typeof json.detail === 'string') {
      return isRateLimitSignal(status, json.detail) ? RATE_LIMIT_USER_MESSAGE : json.detail;
    }
    if (json.detail && typeof json.detail === 'object' && !Array.isArray(json.detail)) {
      const formatted = formatStructuredDetail(json.detail as ApiErrorDetailObject);
      if (formatted) return formatted;
    }
    if (Array.isArray(json.detail)) {
      return json.detail
        .map((item) =>
          typeof item === 'object' && item && 'msg' in item ? String(item.msg) : String(item),
        )
        .join('; ');
    }
  } catch {
    // not JSON
  }

  return trimmed.length > 280 ? `${trimmed.slice(0, 280)}…` : trimmed;
}
