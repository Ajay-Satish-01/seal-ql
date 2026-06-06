import { PageHeader } from '@/components/page-header';
import { Callout } from '@/components/docs/callout';
import { CodeBlock } from '@/components/code-block';
import Link from 'next/link';

export default function VectorRagPage() {
  return (
    <div className="w-full">
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

      <h2 className="font-heading mt-8 text-xl font-semibold">Embeddings</h2>
      <p className="text-muted-foreground mt-2 text-sm">
        Default <code>EMBEDDING_MODEL=text-embedding-3-small</code> uses OpenAI via LiteLLM. Set{' '}
        <code>OPENAI_API_KEY</code> or <code>LLM_API_KEY</code> in <code>.env</code> when{' '}
        <code>VECTOR_STORE=chroma</code>. The API logs a startup warning if Chroma is enabled without
        embedding credentials.
      </p>

      <h2 className="font-heading mt-8 text-xl font-semibold">What gets indexed</h2>
      <ul className="text-muted-foreground mt-4 list-disc space-y-2 pl-6 text-sm">
        <li>Data catalog descriptions (after sync)</li>
        <li>Schema table/column comments from introspection</li>
        <li>Optional markdown/text under <code>RAG_DOCUMENTS_PATH</code></li>
      </ul>

      <h2 className="font-heading mt-8 text-xl font-semibold">Reindex</h2>
      <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
        After enabling Chroma, updating catalog descriptions, or adding documents, trigger a
        reindex so the vector store reflects your latest content:
      </p>
      <CodeBlock
        language="bash"
        code={`# Reindex the vector store
curl -s -X POST http://localhost:8000/v1/vector/reindex \\
  -H "X-API-Key: your-api-key"

# Verify enhancement uses vector RAG
curl -s -X POST http://localhost:8000/v1/chat \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: your-api-key" \\
  -d '{"message":"What are the key revenue metrics?"}' \\
  | jq '.metadata.enhancement'`}
      />
      <p className="text-muted-foreground mt-2 text-sm">
        When vector RAG is active, <code>metadata.enhancement.applied</code> includes{' '}
        <code>&quot;vector_rag&quot;</code>. When skipped (non-default database, store disabled),{' '}
        <code>metadata.enhancement.vector_skipped_reason</code> explains why.
      </p>

      <h2 className="font-heading mt-8 text-xl font-semibold">Example response with RAG</h2>
      <CodeBlock
        language="json"
        code={`{
  "metadata": {
    "enhancement": {
      "enabled": true,
      "applied": ["schema_context", "vector_rag", "catalog_descriptions"],
      "vector_skipped_reason": null
    },
    "scope": { "in_scope": true, "source": "heuristic" },
    "used_sql": true
  }
}`}
      />

      <h2 className="font-heading mt-8 text-xl font-semibold">Adding custom documents</h2>
      <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
        Place markdown or text files in <code>RAG_DOCUMENTS_PATH</code> (default{' '}
        <code>/app/rag-docs</code> inside the container). These are chunked and embedded alongside
        catalog text:
      </p>
      <CodeBlock
        language="bash"
        code={`# Mount a local directory with your documents
# In docker-compose.yml:
#   volumes:
#     - ./rag-docs:/app/rag-docs

# Example document: rag-docs/revenue-glossary.md
# Contains: "Revenue is calculated as SUM(amount) from the orders table..."

# After adding documents, reindex:
curl -s -X POST http://localhost:8000/v1/vector/reindex \\
  -H "X-API-Key: your-api-key"`}
      />

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
        . Provenance details including RAG usage:{' '}
        <Link href="/docs/trust-explainability" className="text-primary underline-offset-4 hover:underline">
          Trust &amp; explainability
        </Link>
        .
      </p>
    </div>
  );
}
