import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';
import { DocsProse } from '@/components/docs/docs-prose';

export default function LocalEvalsPage() {
  return (
    <div className="w-full">
      <PageHeader
        title="Local planner evals"
        description="Grade the query planner against a fixed dataset on your machine."
      />

      <DocsProse>
        <p>
          The harness in <code>evals/seal_evals/runner.py</code> runs each line in{' '}
          <code>evals/data/eval_set.jsonl</code> (public benchmark; see{' '}
          <code>EVAL_SET_EXPECTED_*</code> in <code>evals/seal_evals/runner.py</code> — analytics,
          TimescaleDB/dialect-sensitive
          cases, and <code>should_fail</code> safety negatives) through the same planner and SQLGlot
          boundary used in production, then optionally executes validated SQL against your seeded
          Postgres database.
        </p>

        <h2>Prerequisites</h2>
        <ul>
          <li>
            <code>.env</code> from <code>.env.example</code> with <code>SEAL_API_KEY</code> and LLM
            settings (Ollama via compose, or cloud with <code>OLLAMA_PROFILE=disabled</code>).
          </li>
          <li>
            <code>make up</code> then <code>make seed</code> for deterministic demo schema and data.
          </li>
        </ul>

        <h2>Commands</h2>
        <CodeBlock
          language="bash"
          code={`make up && make seed

# Validation only (recommended first)
make eval-planner

# Full path: validate + execute on Postgres
make eval

# On host (optional; ARGS overrides CLI default localhost URL)
make eval-local EVAL_PLANNER=1

# Bare CLI (same default DB URL after make up && make seed)
uv run python evals/seal_evals/runner.py --planner-only

# Unit tests (no LLM)
uv run pytest evals/tests/test_runner.py -v`}
        />
        <p>
          JSONL rows must include only <code>question</code> (string) and <code>should_fail</code>{' '}
          (boolean). Omitting <code>database_url</code> targets seeded Postgres on{' '}
          <code>localhost:5432</code> — not an in-memory database.
        </p>

        <h2>Model and dialect comparison</h2>
        <p>
          Pass <code>--models</code> and/or <code>--dialect-urls</code> for side-by-side matrix runs on
          the same JSONL. Output includes <code>&quot;comparison&quot;: true</code> and a{' '}
          <code>runs</code> array with one result per dialect URL × model. Exit code{' '}
          <strong>1</strong> when any leg fails the minimum rate or records hard errors.
        </p>
        <CodeBlock
          language="bash"
          code={`# Compare two local Ollama models (planner-only smoke)
uv run python evals/seal_evals/runner.py --planner-only \\
  --models ollama/llama3.2:1b,ollama/qwen2.5:3b

# Compare Postgres vs in-memory DuckDB
uv run python evals/seal_evals/runner.py --planner-only \\
  --dialect-urls postgresql+asyncpg://postgres:postgres@localhost:5432/seal,duckdb:///:memory:

# Via Make (comma-separated MODELS / DIALECT_URLS)
MODELS=ollama/llama3.2:1b,ollama/qwen2.5:3b EVAL_PLANNER=1 make eval-compare`}
        />

        <h2>Interpreting results</h2>
        <p>
          The CLI prints JSON with <code>validation_rate</code> (planner-only) or{' '}
          <code>execution_rate</code> (full eval), <code>scored_queries</code>,{' '}
          <code>expected_failures_caught</code> for negative cases, and <code>errors</code>. Exit code{' '}
          <strong>0</strong> only when there are no errors and the success rate is at least the minimum
          (default <strong>0.6</strong>, override with <code>EVAL_MIN_RATE=0.3 make eval-planner</code>
          ).
        </p>
        <p>
          Cloud quota errors (HTTP 429) and Ollama connection failures are treated as eval failures,
          not skips. Use a local model or wait for quota reset before trusting a low score.
        </p>

        <p>
          Maintainer reference: <code>docs/local-evals.md</code> and{' '}
          <Link href="/docs/contributing">Contributing</Link>.
        </p>
      </DocsProse>
    </div>
  );
}
