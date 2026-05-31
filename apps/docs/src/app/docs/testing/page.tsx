import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { Callout } from '@/components/docs/callout';
import { DocsProse } from '@/components/docs/docs-prose';

export default function TestingPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Testing & CI"
        description="How Seal validates changes — fast mocked unit tests locally and live end-to-end suites in CI."
      />

      <DocsProse>
        <p>
          Seal splits validation into two speeds. <strong>Unit and integration tests</strong> mock
          LLM providers and hit in-process FastAPI clients so every pull request gets deterministic
          feedback in a few minutes. <strong>End-to-end tests</strong> assume a real Docker stack on
          port 8000 with Ollama or a cloud model and exercise the same paths your SDK users call in
          production.
        </p>
        <p>
          Understanding which command runs which layer saves time: <code>make check</code> is what
          most contributors run before pushing; <code>make check-e2e</code> is the optional live
          stack gate that mirrors the dedicated CI job.
        </p>

        <h2>What runs in CI</h2>
        <p>
          GitHub Actions runs jobs in parallel on every pull request to <code>main</code>. The Python
          test job keeps Postgres and the API container up but excludes files that require a healthy
          LLM. A separate E2E job starts the full compose profile (including Ollama when configured)
          and runs HTTP-based SDK tests plus API integration tests.
        </p>
        <ul>
          <li>
            <strong>Python — Tests</strong> — Hundreds of tests using <code>TestClient</code> and
            mocks; catalog, workspace, guardrails, and SQL validation without billing your LLM
            provider.
          </li>
          <li>
            <strong>E2E Tests (Python &amp; TypeScript)</strong> — Live stack;{' '}
            <code>test_sdk_e2e.py</code>, <code>test_e2e.py</code>,{' '}
            <code>test_catalog_workspace_integration.py</code>, and the TypeScript SDK Vitest suite.
          </li>
          <li>
            <strong>Docs &amp; dashboard builds</strong> — Ensures the marketing/docs site and
            operational dashboard compile; catches broken imports such as the linked{' '}
            <code>seal</code> TypeScript SDK in the demo.
          </li>
        </ul>

        <Callout variant="info" title="LLM E2E behavior">
          Chat and query E2E tests <strong>skip with a warning</strong> when the provider returns
          rate limits (HTTP 429), server errors, or timeouts — so flaky cloud quotas do not block
          unrelated merges. They <strong>fail</strong> on auth regressions, incorrect scope decisions,
          or silent success responses (empty assistant text, missing SQL when data was required).
        </Callout>

        <h2>Local commands</h2>
        <p>
          Run these from the repository root unless noted. Ensure <code>.env</code> exists (copy
          from <code>.env.example</code>) so <code>make up</code> can read <code>SEAL_API_KEY</code>{' '}
          and LLM settings.
        </p>
        <CodeBlock
          language="bash"
          code={`# Full lint + unit tests + builds (mirrors most of CI)
make check

# Live E2E (requires stack)
make up && make seed
make check-e2e

# All pytest inside API container
docker compose exec api uv run pytest -v

# Unit only (same as CI python-test job)
docker compose exec -T api uv run pytest -v \\
  --ignore=sdks/python/tests/test_sdk_e2e.py \\
  --ignore=apps/api/tests/test_e2e.py \\
  --ignore=apps/api/tests/test_catalog_workspace_integration.py`}
        />

        <h3>What each command gives you</h3>
        <p>
          <strong><code>make check</code></strong> — Runs Ruff, pytest with E2E files ignored,
          OpenAPI sync verification, and production builds for <code>apps/docs</code> and{' '}
          <code>apps/web</code>. Expect a green summary locally to match the majority of CI; it does{' '}
          <em>not</em> call a live LLM.
        </p>
        <p>
          <strong><code>make check-e2e</code></strong> — Assumes containers are already healthy on
          port 8000. Expect several minutes of runtime and possible skips if Ollama is down or your
          cloud key is missing; failures on 401/403 almost always mean auth configuration drift.
        </p>
        <p>
          <strong>Docker pytest invocations</strong> — Use the same interpreter and mounted source
          tree as CI. The ignore flags match the unit job exactly so you can reproduce CI failures
          without running expensive E2E files.
        </p>

        <h2>What each E2E suite covers</h2>
        <p>
          Use this table to decide which log to open when an E2E job fails. All HTTP suites target{' '}
          <code>http://localhost:8000</code> with <code>X-API-Key</code> from your environment.
        </p>

        <div className="not-prose border-border/50 my-6 overflow-x-auto rounded-xl border text-sm">
          <table className="w-full min-w-[32rem] text-left">
            <thead>
              <tr className="border-border/50 bg-muted/40 border-b">
                <th className="text-foreground px-4 py-3 font-semibold">Suite</th>
                <th className="text-foreground px-4 py-3 font-semibold">Transport</th>
                <th className="text-foreground px-4 py-3 font-semibold">Covers</th>
                <th className="text-foreground px-4 py-3 font-semibold">Typical failure signal</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground divide-border/40 divide-y">
              <tr>
                <td className="px-4 py-2 font-mono text-xs">test_sdk_e2e.py</td>
                <td className="px-4 py-2">HTTP :8000</td>
                <td className="px-4 py-2">Python SDK — health, schema, catalog, chat, query</td>
                <td className="px-4 py-2">Connection refused (stack down) or SDK/ API contract mismatch</td>
              </tr>
              <tr>
                <td className="px-4 py-2 font-mono text-xs">test_e2e.py</td>
                <td className="px-4 py-2">TestClient + real DB</td>
                <td className="px-4 py-2">Full app paths — catalog PATCH/sync, chat, query</td>
                <td className="px-4 py-2">Scope or SQL validation errors surfaced as 400/200 refusal</td>
              </tr>
              <tr>
                <td className="px-4 py-2 font-mono text-xs">test_catalog_workspace_integration.py</td>
                <td className="px-4 py-2">HTTP :8000</td>
                <td className="px-4 py-2">Catalog overrides + Postgres workspace storage</td>
                <td className="px-4 py-2">Skipped when API unreachable; fails if overrides lost after sync</td>
              </tr>
              <tr>
                <td className="px-4 py-2 font-mono text-xs">sdks/typescript e2e.test.ts</td>
                <td className="px-4 py-2">HTTP :8000</td>
                <td className="px-4 py-2">TypeScript SDK parity with Python E2E</td>
                <td className="px-4 py-2">Timeouts on slow LLM (suite uses extended Vitest timeout)</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2>Branch protection</h2>
        <p>
          Repository maintainers can require the <strong>E2E Tests (Python &amp; TypeScript)</strong>{' '}
          check in branch protection so merges always exercised a live stack. Unit-only forks may
          omit that requirement but should still run <code>make check</code> locally.
        </p>

        <p>
          Contributor workflow and docs-site tooling: <Link href="/docs/contributing">Contributing</Link>
          . Environment variables that affect test behavior:{' '}
          <Link href="/docs/configuration">Configuration reference</Link>.
        </p>
      </DocsProse>
    </div>
  );
}
