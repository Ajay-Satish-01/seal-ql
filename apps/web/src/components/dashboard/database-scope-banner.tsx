'use client';

import { useConnection } from '@/hooks/use-connection';
import { DEFAULT_DATABASE_ID } from '@/lib/connection';

type DatabaseScopeBannerProps = {
  /** Short label for what is default-scoped (e.g. "Catalog sync"). */
  feature: string;
};

export function DatabaseScopeBanner({ feature }: DatabaseScopeBannerProps) {
  const { databaseId } = useConnection();
  if (databaseId === DEFAULT_DATABASE_ID) return null;

  return (
    <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-950 dark:text-amber-100">
      <strong className="font-medium">Using database &quot;{databaseId}&quot;.</strong> {feature}{' '}
      applies to the <code className="font-mono text-xs">default</code> database only. Query and
      chat use your selected database; switch to <code className="font-mono text-xs">default</code>{' '}
      in the connection bar for catalog-aligned behavior.
    </div>
  );
}
