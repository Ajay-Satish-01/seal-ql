const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });

/** Format an ISO timestamp as a short relative label (e.g. "2 min ago"). */
export function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const diffSec = Math.round((Date.now() - then) / 1000);
  const abs = Math.abs(diffSec);
  if (abs < 60) return rtf.format(-diffSec, 'second');
  if (abs < 3600) return rtf.format(-Math.round(diffSec / 60), 'minute');
  if (abs < 86400) return rtf.format(-Math.round(diffSec / 3600), 'hour');
  return rtf.format(-Math.round(diffSec / 86400), 'day');
}
