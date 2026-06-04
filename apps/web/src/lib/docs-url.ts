/** Docs site base URL for help links (no trailing slash). */
export const DEFAULT_DOCS_URL =
  (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_DOCS_URL) || 'http://localhost:3000';

export function docsPageUrl(path: string): string {
  const base = DEFAULT_DOCS_URL.replace(/\/+$/, '');
  const suffix = path.startsWith('/') ? path : `/${path}`;
  return `${base}${suffix}`;
}
