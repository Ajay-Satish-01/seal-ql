import { PageHeader } from '@/components/page-header';
import { Callout } from '@/components/docs/callout';
import { CodeBlock } from '@/components/code-block';
import Link from 'next/link';

export default function VectorRagPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Vector RAG"
        description="Optional Chroma-backed retrieval over catalog, schema comments, and document folders."
      />
      <Callout variant="warning" title="Default: off">
        <code>VECTOR_STORE=none</code> skips vector RAG. The schema + catalog enhancers still run.
      </Callout>

      <h2 className="font-heading mt-8 text-xl font-semibold">Enable Chroma (self-host)</h2>
      <CodeBlock
        language="bash"
        code={`# In .env for docker-compose
VECTOR_STORE=chroma

# Contributors: install optional extra, then restart API
uv sync --all-packages --all-extras
# seal-core[chroma] on Linux Docker images`}
      />

      <h2 className="font-heading mt-8 text-xl font-semibold">Configuration</h2>
      <CodeBlock
        language="bash"
        code={`VECTOR_STORE=none              # default
VECTOR_STORE=chroma              # reference implementation
VECTOR_STORE_CLASS=my.store.Store # any Python class implementing VectorStore
VECTOR_STORE_CONFIG='{"persist_directory":"/data/chroma"}'

RAG_DOCUMENTS_PATH=/app/rag-docs
RAG_TOP_K=5
RAG_MAX_CONTEXT_TOKENS=1500`}
      />

      <h2 className="font-heading mt-8 text-xl font-semibold">What gets indexed</h2>
      <ul className="text-muted-foreground mt-4 list-disc space-y-2 pl-6 text-sm">
        <li>Data catalog descriptions (after sync)</li>
        <li>Schema table/column comments from introspection</li>
        <li>Optional markdown/text under <code>RAG_DOCUMENTS_PATH</code></li>
      </ul>

      <p className="text-muted-foreground mt-6 text-sm">
        When using LangChain/Mastra with their own RAG, set <code>VECTOR_STORE=none</code> and{' '}
        <code>enhancement: false</code> on chat — see{' '}
        <Link href="/docs/agent-frameworks" className="text-primary underline-offset-4 hover:underline">
          Agent frameworks
        </Link>
        . Persist volumes on{' '}
        <Link href="/docs/self-hosting" className="text-primary underline-offset-4 hover:underline">
          Self-Hosting
        </Link>
        .
      </p>
    </div>
  );
}
