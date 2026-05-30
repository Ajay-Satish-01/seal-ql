import { PageHeader } from '@/components/page-header';
import { Callout } from '@/components/docs/callout';
import { CodeBlock } from '@/components/code-block';
import Link from 'next/link';
import { SITE } from '@/lib/constants';
export default function PromptEnhancementPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Prompt enhancement"
        description="Vanna-style hooks: schema, vector RAG, and multi-turn memory chained per chat turn."
      />
      <Callout variant="info" title="Default chain">
        SchemaAware → VectorRag (when <code>VECTOR_STORE</code> ≠ <code>none</code>) → MultiTurn.
        Applies to <code>POST /v1/chat</code> when <code>CHAT_ENHANCEMENT_ENABLED=true</code>.
      </Callout>

      <h2 className="font-heading mt-8 text-xl font-semibold">Environment</h2>
      <CodeBlock
        language="bash"
        code={`# docker-compose / .env
CHAT_ENHANCEMENT_ENABLED=true
CHAT_MAX_HISTORY_MESSAGES=20
CHAT_SUMMARIZE_AFTER_MESSAGES=12
VECTOR_STORE=none
# VECTOR_STORE=chroma   # requires seal-core[chroma] in the image`}
      />

      <h2 className="font-heading mt-8 text-xl font-semibold">Disable per request</h2>
      <CodeBlock
        language="bash"
        code={`curl -s -X POST "${SITE.defaultBaseUrl}/v1/chat" \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: your-api-key" \\
  -d '{"message":"Hello","enhancement":false}'`}
      />
      <CodeBlock
        language="python"
        code={`client.chat("Hello", enhancement=False)`}
      />
      <CodeBlock
        language="typescript"
        code={`await client.chat('Hello', { enhancement: false });`}
      />

      <h2 className="font-heading mt-8 text-xl font-semibold">When hooks run</h2>
      <ul className="text-muted-foreground mt-4 list-disc space-y-2 pl-6 text-sm">
        <li>
          <code>enhance_system_prompt</code> — once per user message (before first LLM call)
        </li>
        <li>
          <code>enhance_user_messages</code> — before each stage: decision, planner, answer
        </li>
      </ul>

      <h2 className="font-heading mt-8 text-xl font-semibold">Custom enhancers</h2>
      <p className="text-muted-foreground mt-4 text-sm leading-relaxed">
        Append dotted paths via <code>SEAL_ENHANCERS=my_package.MyEnhancer</code>. Each enhancer
        implements <code>PromptEnhancer</code> and fails open on errors. Vector settings:{' '}
        <Link href="/docs/vector-rag" className="text-primary underline-offset-4 hover:underline">
          Vector RAG
        </Link>
        . Catalog context:{' '}
        <Link href="/docs/data-catalog" className="text-primary underline-offset-4 hover:underline">
          Data catalog
        </Link>
        .
      </p>
    </div>
  );
}
