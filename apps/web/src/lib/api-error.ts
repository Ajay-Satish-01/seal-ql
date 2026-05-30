/** Extract a human-readable message from Seal API error responses. */
export function formatApiError(status: number, bodyText: string): string {
  const trimmed = bodyText.trim();
  if (!trimmed) return `Request failed (${status})`;

  try {
    const json = JSON.parse(trimmed) as { detail?: unknown };
    if (typeof json.detail === 'string') return json.detail;
    if (Array.isArray(json.detail)) {
      return json.detail
        .map((item) => (typeof item === 'object' && item && 'msg' in item ? String(item.msg) : String(item)))
        .join('; ');
    }
  } catch {
    // not JSON
  }

  return trimmed.length > 280 ? `${trimmed.slice(0, 280)}…` : trimmed;
}
