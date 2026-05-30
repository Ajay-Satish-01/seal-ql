import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { Callout } from '@/components/docs/callout';
import { SITE } from '@/lib/constants';

export default function ContributingPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Contributing"
        description="Develop from source — for maintainers and contributors, not required for integration."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <Callout variant="warning" title="Not the default install path">
          If you only want to <em>use</em> Intelligence Connector, follow{' '}
          <Link href="/docs/self-hosting">Self-Hosting</Link> (Docker) and the{' '}
          <Link href="/docs/integration-guide">Integration Guide</Link> (SDK). Clone when you need
          to change core code.
        </Callout>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Clone and run the stack</h2>
        <CodeBlock
          language="bash"
          code={`git clone ${SITE.github}.git
cd intelligence-connector
cp .env.example .env   # Ollama (default) or OLLAMA_PROFILE=disabled + cloud API keys
make up
make seed
uv run pytest -v`}
        />
        <p>
          See <code>.env.example</code> and{' '}
          <Link href="/docs/self-hosting#llm-configuration">LLM configuration</Link> for LiteLLM{' '}
          <code>LLM_MODEL</code> ids and <code>OLLAMA_PROFILE</code> (Ollama vs cloud).
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Tooling</h2>
        <p>
          Node.js <strong>24</strong> for TypeScript and the docs site (see <code>.nvmrc</code> at
          the repo root). With{' '}
          <a
            href="https://github.com/nvm-sh/nvm"
            className="text-primary hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            nvm
          </a>
          : <code>nvm use</code> from the repository root.
        </p>
        <ul>
          <li>
            Python: <code>uv sync --all-packages --all-extras</code>
          </li>
          <li>
            TypeScript SDK: <code>cd sdks/typescript && pnpm install && pnpm build</code>
          </li>
          <li>
            Docs site: build the TypeScript SDK first, then the web app —{' '}
            <code>make check-web</code> or{' '}
            <code>
              cd sdks/typescript && pnpm build && cd ../../apps/web && pnpm install && pnpm dev
            </code>
          </li>
          <li>
            Lint: <code>make lint</code> · full CI: <code>make check</code>
          </li>
        </ul>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Regenerate docs assets</h2>
        <CodeBlock language="bash" code="make sync-docs-assets" />

        <p>Updates OpenAPI spec, demo fixtures, and copies seed SQL into the docs site.</p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Releases</h2>
        <p>Align per release:</p>
        <ul>
          <li>
            Docker image <code>intelligence-connector/api:&lt;tag&gt;</code>
          </li>
          <li>
            PyPI <code>intelligence-connector</code> and npm <code>intelligence-sdk</code>
          </li>
          <li>
            Committed <code>apps/api/openapi.json</code>
          </li>
        </ul>
      </div>
    </div>
  );
}
