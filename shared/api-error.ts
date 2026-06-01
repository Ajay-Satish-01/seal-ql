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

/** Extract a human-readable message from Seal API error responses. */
export function formatApiError(status: number, bodyText: string): string {
  const trimmed = bodyText.trim();
  if (!trimmed) return `Request failed (${status})`;

  try {
    const json = JSON.parse(trimmed) as { detail?: unknown };
    if (typeof json.detail === 'string') return json.detail;
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
