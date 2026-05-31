/** Structured FastAPI error detail (session mismatch, etc.). */
export type ApiErrorDetailObject = {
  code?: string;
  message?: string;
  session_id?: string;
  pinned_database_id?: string;
  requested_database_id?: string;
};

/** Extract a human-readable message from Seal API error responses. */
export function formatApiError(status: number, bodyText: string): string {
  const trimmed = bodyText.trim();
  if (!trimmed) return `Request failed (${status})`;

  try {
    const json = JSON.parse(trimmed) as { detail?: unknown };
    if (typeof json.detail === 'string') return json.detail;
    if (json.detail && typeof json.detail === 'object' && !Array.isArray(json.detail)) {
      const obj = json.detail as ApiErrorDetailObject;
      if (obj.message) return obj.message;
      if (obj.code === 'session_database_id_mismatch') {
        return (
          `Session is pinned to database "${obj.pinned_database_id ?? '?'}" ` +
          `but request used "${obj.requested_database_id ?? '?'}". ` +
          'Start a new chat session or select the pinned database.'
        );
      }
      if (obj.code) return obj.code;
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
