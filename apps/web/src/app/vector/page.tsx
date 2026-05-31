'use client';

import { DatabaseScopeBanner } from '@/components/dashboard/database-scope-banner';
import { PageShell } from '@/components/dashboard/page-shell';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useConnection } from '@/hooks/use-connection';
import { reindexVector } from '@/lib/seal-api';
import { notifyErrorFrom, notifySuccess } from '@/lib/toast';
import { useTransition } from 'react';

export default function VectorPage() {
  const { apiUrl, apiKey } = useConnection();
  const [isPending, startTransition] = useTransition();

  function reindex() {
    startTransition(async () => {
      try {
        const res = await reindexVector(apiUrl, apiKey);
        notifySuccess(`Indexed ${res.indexed_tables} table(s) (${res.status})`);
      } catch (e) {
        notifyErrorFrom(e, 'Reindex failed');
      }
    });
  }

  return (
    <PageShell
      title="Vector index"
      description="POST /v1/vector/reindex when VECTOR_STORE is chroma (or another backend)."
    >
      <DatabaseScopeBanner feature="Vector reindex" />
      <Card className="console-panel space-y-4 p-4">
        <p className="text-muted-foreground text-sm">
          Rebuild embeddings from the live schema and catalog. Requires vector store configuration
          on the API.
        </p>
        <Button onClick={reindex} disabled={isPending}>
          {isPending ? 'Reindexing…' : 'Reindex vector store'}
        </Button>
      </Card>
    </PageShell>
  );
}
