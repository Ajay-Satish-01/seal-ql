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
          If you only want to <em>use</em> Seal, follow{' '}
          <Link href="/docs/self-hosting">Self-Hosting</Link> (Docker) and the{' '}
          <Link href="/docs/integration-guide">Integration Guide</Link> (SDK). Clone when you need
          to change core code.
        </Callout>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Clone and run the stack</h2>
        <CodeBlock
          language="bash"
          code={`git clone ${SITE.github}.git
cd seal
cp .env.example .env
# .env.example sets SEAL_DEV_MODE=true and a placeholder SEAL_API_KEY for local dev.
# For anything shared or production-like, run: openssl rand -hex 32
make up    # fails fast if SEAL_API_KEY is missing in .env
make seed
make sync-catalog
uv run pytest -v

# Smoke-test chat (uses SEAL_API_KEY from .env)
curl -s -X POST http://localhost:8000/v1/chat \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: $SEAL_API_KEY" \\
  -d '{"message":"What tables exist?"}' | python3 -m json.tool`}
        />
        <p>
          See <code>.env.example</code> (auth + LLM vars) and{' '}
          <Link href="/docs/authentication">Authentication</Link> for{' '}
          <code>SEAL_AUTH_REQUIRED</code> / <code>SEAL_DEV_MODE</code>. LLM:{' '}
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
              cd sdks/typescript && pnpm build && cd ../../apps/docs && pnpm install && pnpm dev
            </code>
          </li>
          <li>
            Lint: <code>make lint</code> · full CI: <code>make check</code>
          </li>
          <li>
            Live E2E (stack must be up): <code>make check-e2e</code> — see{' '}
            <Link href="/docs/testing">Testing &amp; CI</Link>
          </li>
        </ul>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Documentation site (apps/docs)</h2>
        <p>
          The docs app is a Next.js site on port <strong>3000</strong>. It links the TypeScript SDK
          from <code>sdks/typescript</code> via <code>pnpm link</code> so the interactive{' '}
          <Link href="/demo">demo</Link> can render <code>VegaChart</code>. <code>pnpm dev</code> runs{' '}
          <code>build:sdk</code> first (see <code>predev</code> in <code>package.json</code>).
        </p>
        <p>
          <code>next.config.ts</code> uses different resolution in development vs production:
        </p>
        <ul>
          <li>
            <strong>Production</strong> — <code>outputFileTracingRoot</code> points at the monorepo
            root so the standalone build traces the linked <code>seal</code> package. Expect{' '}
            <code>pnpm build</code> to succeed in CI without extra aliases.
          </li>
          <li>
            <strong>Development (Turbopack)</strong> — <code>turbopack.root</code> is the repo root so
            the symlinked SDK resolves; narrowing the root to <code>apps/docs</code> alone breaks{' '}
            <code>import &apos;seal&apos;</code> on <code>/demo</code>. Do not set{' '}
            <code>outputFileTracingRoot</code> in dev — it widens file watching and can leave the dev
            server stuck on &quot;Compiling…&quot;.
          </li>
          <li>
            <strong>Webpack fallback</strong> — <code>pnpm dev:webpack</code> uses a direct alias to{' '}
            <code>sdks/typescript</code> if Turbopack misbehaves on your machine.
          </li>
        </ul>
        <p>
          Operator-facing environment variables for the Seal API are documented separately on{' '}
          <Link href="/docs/configuration">Configuration reference</Link> — not in <code>next.config.ts</code>.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Repository documentation</h2>
        <p>
          Maintainer guides in the clone (not rendered as site pages):{' '}
          <code>CONTRIBUTORS.md</code>, <code>DEPLOYMENT.md</code>, <code>SETUP.md</code>, and the{' '}
          <code>docs/</code> tree indexed by <code>docs/README.md</code> (embedding, multi-database,
          guardrails, chat metadata, integrations). When you change API behavior, update the matching{' '}
          <code>docs/*.md</code> file and the corresponding <code>/docs/*</code> page here.
        </p>
        <p>
          Operational dashboard: <code>apps/web</code> on port <strong>3001</strong> — see{' '}
          <Link href="/docs/dashboard">Dashboard</Link>.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Local planner evals</h2>
        <p>
          Grade the query planner on your machine after <code>make up</code> and{' '}
          <code>make seed</code>. This is <strong>not</strong> part of PR CI — see{' '}
          <Link href="/docs/local-evals">Local planner evals</Link> for commands, metrics, and why
          rate limits are not skipped like E2E tests.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Regenerate docs assets</h2>
        <CodeBlock language="bash" code="make sync-docs-assets" />

        <p>
          Updates OpenAPI spec, demo fixtures, <code>seal-tools.openai.json</code>,{' '}
          <code>catalog.example.yaml</code>, and seed SQL into the docs site. After schema changes:{' '}
          <code>make openapi-ts</code> then <code>make verify-openapi-sync</code>.
        </p>

        <h2 className="text-foreground mt-10 text-2xl font-bold">Releases</h2>
        <p>
          See <code>RELEASING.md</code> in the repository root. Push a <code>v*</code> git tag to
          trigger the Release workflow (Docker Hub, PyPI, npm). Align per release:
        </p>
        <ul>
          <li>
            Docker image <code>seal/api:&lt;version&gt;</code>
          </li>
          <li>
            PyPI <code>seal</code> and npm <code>seal</code>
          </li>
          <li>
            Committed <code>uv.lock</code> and <code>apps/api/openapi.json</code>
          </li>
        </ul>
      </div>
    </div>
  );
}
