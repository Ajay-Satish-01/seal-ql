# Local planner evals

Grade the **Query Planner** against a fixed JSONL dataset on your machine.

## Prerequisites

1. Copy [`.env.example`](../.env.example) → `.env` and set `SEAL_API_KEY`.
2. Configure an LLM in `.env` — **Ollama** (default compose) or a cloud provider (`OLLAMA_PROFILE=disabled` + API key).
3. Start the stack and seed demo data:

```bash
make up
make seed
```

`make seed` truncates mutable demo tables then re-applies `scripts/seed.sql` (including Timescale continuous-aggregate refresh).

## Commands

| Command | What it does |
| ------- | ------------- |
| `make eval-planner` | Plan → SQLGlot validate only (fastest smoke test) |
| `make eval` | Plan → validate → execute on seeded Postgres |
| `make eval-local` | Run on host; `ARGS=` DB URL, `EVAL_PLANNER=1` for planner-only |
| `make refresh-cagg` | Refresh `events_hourly` / `events_daily` without full re-seed |

Lower the pass threshold for experiments:

```bash
EVAL_MIN_RATE=0.3 make eval-planner
```

## Dataset

- **Path:** `evals/data/eval_set.jsonl` (20 NL questions on the seed schema, including `should_fail` safety cases).
- **Runner:** `evals/seal_evals/runner.py`

## Exit codes and metrics

- Default `--min-execution-rate` is **0.6** (exit **1** if scored cases fall below that rate or any hard `errors`).
- Rates use `scored_queries` (excludes `should_fail` negative cases).
- `make eval-planner` reports `validation_rate`; `make eval` reports `execution_rate`.
- Per-case timeout defaults to `query_timeout_seconds × 3 + 120` (`--query-timeout` to override).

Cloud quota errors (HTTP 429) and Ollama connection failures count as eval failures — use a local model or wait for quota reset before trusting a low score.

## Unit tests (no LLM)

```bash
uv run pytest evals/tests/test_runner.py -v
```

## Docs site

User-facing copy: `/docs/local-evals` on the docs app (port 3000).
