/**
 * Parse FastAPI error bodies into SDK exceptions.
 */

import { QueryError, QueryOutOfScopeError, ServerError } from './errors.js';

const MAX_SUGGESTION_CHARS = 200;

function parseSuggestedQueries(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  const cleaned: string[] = [];
  for (const item of raw) {
    if (typeof item !== 'string') continue;
    const text = item.trim();
    if (!text) continue;
    cleaned.push(text.slice(0, MAX_SUGGESTION_CHARS));
    if (cleaned.length >= 3) break;
  }
  return cleaned;
}

function formatOutOfScopeMessage(reason: string, suggestedQueries: string[]): string {
  const reasonSuffix = reason ? ` (${reason})` : '';
  const hint =
    suggestedQueries.length > 0
      ? `. Try: ${suggestedQueries.map((q) => `"${q}"`).join(' · ')}`
      : '';
  return `Query out of scope${reasonSuffix}${hint}`;
}

function detailToMessage(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const obj = detail as Record<string, unknown>;
    if (typeof obj.message === 'string' && obj.message.trim()) return obj.message;
    if (obj.detail === 'query_out_of_scope') {
      const reason = typeof obj.reason === 'string' ? obj.reason : '';
      const suggested = parseSuggestedQueries(obj.suggested_queries);
      return formatOutOfScopeMessage(reason, suggested);
    }
    if (obj.code === 'session_database_id_mismatch') {
      return (
        `Session is pinned to database "${obj.pinned_database_id ?? '?'}" ` +
        `but request used "${obj.requested_database_id ?? '?'}". ` +
        'Start a new chat session or select the pinned database.'
      );
    }
    if (typeof obj.code === 'string') return obj.code;
  }
  return String(detail);
}

export function raiseForResponse(status: number, body: { detail?: unknown }): never {
  const detail = body.detail ?? 'Request failed';

  if (status >= 500) {
    throw new ServerError(`Server error (${status}): ${detailToMessage(detail)}`, status);
  }

  if (
    status >= 400 &&
    detail &&
    typeof detail === 'object' &&
    !Array.isArray(detail) &&
    (detail as Record<string, unknown>).detail === 'query_out_of_scope'
  ) {
    const obj = detail as Record<string, unknown>;
    const reason = typeof obj.reason === 'string' ? obj.reason : '';
    const suggestedQueries = parseSuggestedQueries(obj.suggested_queries);
    const message = formatOutOfScopeMessage(reason, suggestedQueries);
    throw new QueryOutOfScopeError(message, status, reason, suggestedQueries);
  }

  throw new QueryError(`Query rejected (${status}): ${detailToMessage(detail)}`, status);
}
