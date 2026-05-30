import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { Callout } from '@/components/docs/callout';
import { SITE } from '@/lib/constants';
import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export default function QuickstartPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Quickstart"
        description="Evaluate, deploy, and integrate — without cloning the repository."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <Callout variant="success" title="No clone required">
          The recommended path uses the published Docker image and SDK packages. Clone the repo only
          if you are <Link href="/docs/contributing">developing from source</Link>.
        </Callout>

        <h2 className="text-foreground mt-10 text-2xl font-bold">1. Explore the demo</h2>
        <p>
          See the full NL → SQL → chart flow in your browser with pre-generated fixtures aligned to
          our sample analytics schema.
        </p>
        <Link href="/demo" className={cn(buttonVariants(), 'no-underline')}>
          Open interactive demo
        </Link>

        <h2 className="text-foreground mt-10 text-2xl font-bold">2. Run with Docker</h2>
        <p>Pull the API image and start the stack (Postgres + Ollama + API):</p>
        <CodeBlock
          language="bash"
          code={`docker pull ${SITE.dockerImage}
mkdir seal-quickstart && cd seal-quickstart
curl -O https://raw.githubusercontent.com/seal/seal/main/apps/web/public/compose/docker-compose.example.yml
curl -O https://raw.githubusercontent.com/seal/seal/main/apps/web/public/samples/seed.sql

# Production .env (generate a real key — do not use placeholders)
printf '%s\\n' \\
  "SEAL_API_KEY=$(openssl rand -hex 32)" \\
  "SEAL_AUTH_REQUIRED=true" \\
  "SEAL_DEV_MODE=false" \\
  "SEAL_DISABLE_DOCS=true" \\
  > .env

docker compose -f docker-compose.example.yml up -d
curl http://localhost:8000/health`}
        />
        <p>
          Full details: <Link href="/docs/self-hosting">Self-Hosting</Link> ·{' '}
          <Link href="/docs/authentication">Authentication</Link>. Production requires a generated{' '}
          <code>SEAL_API_KEY</code>; the example compose rejects placeholders at startup.
        </p>

        <Callout variant="info" title="Develop from source">
          Clone the repo, <code>cp .env.example .env</code> (placeholder key is OK with{' '}
          <code>SEAL_DEV_MODE=true</code>), then <code>make up</code> and <code>make seed</code>.
          See <Link href="/docs/contributing">Contributing</Link>.
        </Callout>

        <Callout variant="info" title="LLM (LiteLLM)">
          Models use LiteLLM ids such as <code>ollama/llama3.2:1b</code> or{' '}
          <code>gemini/gemini-1.5-flash</code>. Local Ollama: default profile +{' '}
          <code>LLM_BASE_URL</code>. Cloud: <code>OLLAMA_PROFILE=disabled</code> + provider API key
          (<code>LLM_API_KEY</code>, <code>GEMINI_API_KEY</code>, etc.). See{' '}
          <Link href="/docs/self-hosting#llm-configuration">LLM configuration</Link>.
        </Callout>

        <h2 className="text-foreground mt-10 text-2xl font-bold">3. Integrate with the SDK</h2>
        <CodeBlock
          language="bash"
          code="pip install seal\n# or\nnpm install seal"
        />
        <CodeBlock
          language="python"
          code={`import os
from seal import Seal

with Seal(
    "${SITE.defaultBaseUrl}",
    api_key=os.environ["SEAL_API_KEY"],
) as client:
    result = client.query("Show total revenue by product category")
    print(result.sql)
    print(result.results)
    if result.chart:
        print(result.chart.chart_type)`}
        />
        <p>
          See the <Link href="/docs/integration-guide">Integration Guide</Link> and SDK docs for
          TypeScript, charts, and error handling.
        </p>
      </div>
    </div>
  );
}
