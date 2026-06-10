# 👥 Contributors & Developer Guide

Thank you for contributing to **Seal**! This document covers repository layout, local setup, coding standards, testing, and pull request expectations.

| Guide | Purpose |
| ----- | ------- |
| **[docs/README.md](docs/README.md)** | Index of all contributor markdown under `docs/` |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | Self-hosting Docker, production env, multi-database |
| **[SETUP.md](SETUP.md)** | SDK install, auth, catalog/chat quick reference |
| **[RELEASING.md](RELEASING.md)** | Version bumps and publish workflow |
| **[AGENTS.md](AGENTS.md)** | Rules for AI coding assistants |

User-facing documentation is built from **`apps/docs`** (port 3000). The operational dashboard is **`apps/web`** (port 3001).

---

## 📚 Documentation map

Contributor prose lives in **`docs/`**; the docs site mirrors it under `/docs/*`. When you change behavior, update **both** the markdown file and the matching Next.js page when one exists.

| Topic | Contributor | Docs site |
| ----- | ----------- | --------- |
| Embedding / BFF / boundaries | [docs/embedding.md](docs/embedding.md) | `/docs/embedding` |
| Pipeline & LLM stages | [docs/how-seal-works.md](docs/how-seal-works.md) | `/docs/how-it-works` |
| `database_id` routing | [docs/multi-database.md](docs/multi-database.md) | `/docs/multi-database` |
| Execution metadata | [docs/chat-metadata.md](docs/chat-metadata.md) | `/docs/execution-metadata` |
| Guardrails & `suggested_queries` | [docs/guardrails.md](docs/guardrails.md) | `/docs/guardrails` |
| Zero-trust SQL (SQLGlot) | [docs/zero-trust-sql.md](docs/zero-trust-sql.md) | `/docs/zero-trust-sql` |
| Chat enhancement / RAG | [docs/chat-enhancement.md](docs/chat-enhancement.md) | `/docs/prompt-enhancement`, `/docs/vector-rag` |
| Workspace API | [docs/workspace-api.md](docs/workspace-api.md) | `/docs/workspace` |
| Extensions (agents, RAG, enhancers) | [docs/integrations/](docs/integrations/) | `/docs/agent-frameworks`, etc. |
| Self-hosting / production env | [DEPLOYMENT.md](DEPLOYMENT.md) | `/docs/self-hosting` |
| Releases | [RELEASING.md](RELEASING.md) | — |

Full index: **[docs/README.md](docs/README.md)**.

---

## 🏛️ Codebase Structure

We use a monorepo architecture managed by modern tooling:

* **Backend (Python)**: Configured as a unified `uv` workspace. The workspace root `pyproject.toml` references:
  * `apps/api` (FastAPI app container)
  * `packages/core` (Planner, chat, catalog, enhancement, guardrails, workspace, vector RAG, introspection, **`database/`** registry, shared **`pipeline/`**)
  * `packages/sql` (AST-based SQL validators)
  * `packages/charts` (Vega-Lite visual generators)
  * `packages/semantic` (Metrics semantic compiler)
  * `sdks/python` (Python SDK wrapper)
  * `evals` (Testing datasets & repair evaluations)
* **Frontend (TypeScript)**:
  * `apps/docs` — docs site + fixture demo (port 3000, `pnpm`)
  * `apps/web` — operational dashboard (port 3001, `pnpm`)
  * `shared/` — stream-meta, metadata-contract, metadata-summary (imported by docs + dashboard; vendored into the TS SDK on `prebuild`)
  * `sdks/typescript/` — published `seal` npm package (OpenAPI-generated wire types in `src/generated/openapi.ts`)

---

## 🛠️ Step-by-Step Development Setup

To establish a complete, working developer environment:

### 1. Repository Setup & Dependencies
```bash
# Clone the repository
git clone https://github.com/seal/seal.git
cd seal

# Initialize Python virtual environment & sync workspace
uv sync --all-packages --all-extras

# Setup TypeScript environment
cd sdks/typescript
pnpm install
cd ../..
```

### 2. Local Stack Startup
```bash
# Boot PostgreSQL (TimescaleDB), Ollama, and API server
make up

# Seed Postgres with sample analytics data
make seed

# Optional: sync data catalog YAML from live schema
make sync-catalog

# Docs site (port 3000) and dashboard (port 3001) — separate terminals
make sync-docs-assets
cd apps/docs && pnpm install && pnpm dev
cd apps/web && pnpm install && pnpm dev
```

### 3. Pre-commit & Push Hook Installation
```bash
# Install local validation hooks
make setup
```

### 4. Workspace schema

The API applies `scripts/migrate_app.sql` on startup (`workspace_store.ensure_schema()` and chat session schema). After `make up`, no manual migrate is required for normal local dev. Run `docker compose exec -T postgres psql -U postgres -d seal < scripts/migrate_app.sql` only when touching Postgres without starting the API.

### 5. Full validation (CI mirror)
```bash
make check          # lint, unit tests, metadata contract, OpenAPI sync, docs + dashboard builds
make check-e2e      # live HTTP E2E — requires `make up` + `make seed`
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for production Docker and [RELEASING.md](RELEASING.md) before tagging releases.

---

## 🔄 Development & Branching Workflow

### 🌿 Git Branch Policy

We use short-lived feature branches cut from `main`. Follow this lifecycle:

1. **Create Branch**: Cut a branch with an active, descriptive prefix:
   ```bash
   git checkout -b feature/your-feature-name
   # OR
   git checkout -b fix/issue-name
   # OR
   git checkout -b ci_workflows
   ```
2. **Work Locally**: Build your changes, keeping commits granular and descriptive. Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`, etc.) — enforced by the `commit-msg` pre-commit hook after `make setup`.
3. **Run Validation**: Ensure all formats, lints, and tests pass before committing:
   ```bash
   pre-commit run --all-files
   ```
4. **Push & PR**: Push to remote and open a Pull Request against `main`.

---

## 🎨 Coding Standards & Linting

We enforce strict formatting rules to maintain maximum readability and zero boilerplate issues.

### 🐍 Python Coding Standards
* **Formatter & Linter**: We use [Ruff](https://github.com/astral-sh/ruff) for lightning-fast checking and formatting.
* **Configuration**: Defined in the root `pyproject.toml` (`line-length = 100`).
* **Hook Trigger**: Auto-formatted and linted on `git commit`.
* **Manual execution**:
  ```bash
  # Auto-format and auto-fix lints
  make format
  ```

### 🟦 TypeScript Coding Standards
* **Formatter**: [Prettier](https://prettier.io/) for unified formatting styling.
* **Linter**: [ESLint](https://eslint.org/) (Flat Config v9+). `make lint` / `make format` cover **Python (Ruff)** and **`sdks/typescript/`** only. When you change `apps/docs` or `apps/web`, run their scripts locally and rely on `make check-docs` / `make check-dashboard` (or full `make check`) for production builds.
* **Manual execution**:
  ```bash
  make lint && make format              # Ruff + TypeScript SDK

  cd apps/docs && pnpm run lint && pnpm run format    # docs site
  cd apps/web && pnpm run lint && pnpm run format     # dashboard
  make check-docs && make check-dashboard             # Next.js build gate
  ```

---

## 🧠 Semantic Metrics, Repair Loops, & Evals

Seal features self-correcting query mechanisms and domain-aware schema reasoning to provide robust and accurate SQL generation.

### 📊 Semantic Metric Layers
**Purpose**: To bridge the gap between raw database schemas and business logic.
- Raw tables often have obscure names (`txn_fct`) and lack domain context.
- The **Semantic Metric Layer** (powered by `packages/semantic`) defines Pydantic models (`Metric`, `Dimension`) mapped via declarative YAML files.
- **Workflow**:
  1. At startup, the FastAPI app initializes a `SemanticRegistry` which loads YAML definitions from the configured `SEMANTIC_DIRECTORY`.
  2. The `QueryPlanner` injects metrics into the prompt for **`database_id=default`** only (global semantic registry today).
  3. The LLM can then reason over logical business concepts ("Revenue", "Active Users") rather than raw columns, significantly improving generation accuracy.

### 🔄 Repair Loops
**Purpose**: To gracefully recover from LLM hallucinations or SQL Dialect syntax errors without failing the user's request.
- **Workflow**:
  1. When the `QueryPlanner` generates SQL, it immediately passes through the strict `SQLValidator` and `SQLSanitizer`.
  2. If the query is destructive (e.g., contains `DROP` or `DELETE`), uses non-existent columns, or fails execution on the underlying database (e.g., `DuckDB` or `TimescaleDB`), an error is raised.
  3. The API execution route catches these errors and triggers the `QueryPlanner.repair_plan` method.
  4. The LLM is provided with its original failed query and the exact database/validator error message, and is prompted to fix the mistake. This loop can retry up to a configurable number of attempts (e.g., 3).

### 🧪 Local planner evals (not in CI)
**Purpose**: Locally measure planner accuracy, SQL validation, and (optionally) execution against the seeded demo schema.

**Not in GitHub Actions** — LLM rate limits (e.g. Gemini 429) and provider outages make full-dataset evals flaky on PR CI. CI still runs **`evals/tests/`** (no live LLM) inside the normal Python test job.

**Guide:** [docs/local-evals.md](docs/local-evals.md) · docs site `/docs/local-evals`

- **`EvalRunner`** — `evals/seal_evals/runner.py` + **`evals/data/eval_set.jsonl`** (`EVAL_SET_EXPECTED_*` constants; including `should_fail` cases).
- Metrics: `validation_rate` / `execution_rate` over `scored_queries`, plus `timeouts`, `repair_successes`, `expected_failures_caught`. Default `--min-execution-rate` **0.6**; per-case `--query-timeout` = `query_timeout_seconds × 3 + 120`.
- **Local (Docker stack):**
  ```bash
  make up && make seed   # truncate + seed.sql (refreshes events_hourly/events_daily at end)
  make eval              # full path: plan → validate → execute on Postgres
  make eval-planner      # fast path: plan → validate only (--planner-only)
  ```
- **Host / custom URL:** omit `database_url` for the same default as `make eval-local` (`DEFAULT_EVAL_DATABASE_URL` in `evals/seal_evals/runner.py`).
  ```bash
  uv run python evals/seal_evals/runner.py --planner-only
  make eval-local EVAL_PLANNER=1
  make eval-local ARGS="postgresql+asyncpg://postgres:postgres@localhost:5432/seal"  # override
  ```

---

## 📡 API schema and TypeScript types

Request/response shapes are defined in **`apps/api/app/schemas.py`** (Pydantic v2). The TypeScript SDK does **not** duplicate field lists in `types.ts` by hand.

After changing API models or route response types:

```bash
make openapi-ts          # openapi.json + openapi-typescript → sdks/typescript/src/generated/openapi.ts
make sync-docs-assets    # when demo fixtures or docs copies need refresh
make verify-openapi-sync # same gate as CI — must be clean before merge
```

Commit together: `apps/api/openapi.json`, `apps/api/openapi.yaml`, `apps/docs/src/data/openapi.json`, `apps/docs/public/openapi.json`, and `sdks/typescript/src/generated/openapi.ts`.

`scripts/generate_openapi.py` also injects component schemas referenced only in manual route responses (for example `ChatStreamMeta` on SSE). See [sdks/typescript/README.md](sdks/typescript/README.md).

---

## 📊 Execution metadata contract

Query and chat share execution fields (`database_id`, `row_count`, `used_sql`, `enhancement`, `scope`, `refusal`, `sql_error`, etc.). JSON chat nests them under `metadata`; SSE `seal.meta` uses a **flat** object.

| Layer | Location |
|-------|----------|
| Server validation | `packages/core/seal_core/pipeline/validate_metadata.py` |
| Key manifest | `config/stream_meta_metadata_keys.json` |
| Shared TS (docs + dashboard) | `shared/stream-meta.ts`, `shared/metadata-contract.ts`, `shared/chat-sse-events.ts` |
| Contributor reference | [docs/chat-metadata.md](docs/chat-metadata.md) |

When adding or renaming metadata fields, update the manifest, flatten golden (`tests/fixtures/chat_flatten_golden.json`), validation matrix (`tests/fixtures/stream_meta_validation_matrix.json`), and run `make check` (includes `verify:chat-flatten` and stream-meta parity).

---

## 🌐 Multi-database & embedding

| Area | Code | Docs |
| ---- | ---- | ---- |
| Registry & config | `packages/core/seal_core/database/registry.py`, `config.py` | [docs/multi-database.md](docs/multi-database.md) |
| API wiring | `apps/api/app/main.py`, `dependencies.py`, `routes/query.py`, `chat.py`, `schema.py` | `/docs/multi-database` |
| Chat session pin | `packages/core/seal_core/chat/service.py`, `errors.py` | `session_database_id_mismatch` |
| Example config | `config/databases.example.yaml` | [DEPLOYMENT.md](DEPLOYMENT.md) |

- Clients send **ids only** — never connection URLs in JSON bodies.
- Unknown `database_id` → HTTP **404**; chat follow-up mismatch → HTTP **400**.
- Catalog, semantic layer, and vector index remain on **`default`** until per-db resources ship (see **Future work** in [docs/embedding.md](docs/embedding.md)).

**Embedders** — Responsibility split, deployment patterns, three boundaries: [docs/embedding.md](docs/embedding.md). Production: never expose `SEAL_API_KEY` to browsers; use a BFF ([DEPLOYMENT.md](DEPLOYMENT.md#embedding-in-your-product)).

---

## 🛡️ Guardrails

Scope gate runs before SQL, RAG, and planner on `/v1/query` and `/v1/chat`:

| Path | Out of scope |
| ---- | ------------ |
| Query | HTTP **400** — `detail.detail` = `query_out_of_scope`, `reason`, `suggested_queries` (heuristic, no extra LLM) |
| Chat | HTTP **200** — `metadata.refusal`, `metadata.suggested_queries` (+ flat fields on SSE `seal.meta`) |

| Code | Tests |
| ---- | ----- |
| `packages/core/seal_core/guardrails/` | `packages/core/tests/test_guardrails_scope.py`, `test_chat_guardrails.py` |
| Query route 400 shape | `apps/api/tests/test_guardrails_api.py` |
| Suggestions helper | `packages/core/seal_core/guardrails/suggestions.py` |

---

## 🧪 Testing Guidelines

No code should be pushed or merged without comprehensive test coverage.

### 🐍 Python Tests
Python tests are written using `pytest` and `pytest-asyncio` for async database handlers.

* **Locating tests**: Add modules under each package’s `tests/` (e.g. `packages/core/tests/`, `apps/api/tests/`).
* **Test database**: `make up` + `make seed` for Postgres; many API tests use mocks for LLM calls.
* **Focused suites**:
  ```bash
  # Multi-database registry
  uv run pytest packages/core/tests/test_database_registry.py apps/api/tests/test_database_routing.py -v

  # Guardrails
  uv run pytest packages/core/tests/test_guardrails_scope.py packages/core/tests/test_chat_guardrails.py apps/api/tests/test_guardrails_api.py -v

  # Metadata contract (query + chat + SSE parity)
  uv run pytest tests/test_response_validation.py packages/core/tests/test_chat_flatten_contract.py -v
  ```
* **Executing tests**:
  ```bash
  uv run pytest -v              # local venv
  make test                     # inside API container
  make test-cov                 # with coverage HTML
  make check                    # full CI mirror (see Makefile)
  make check-e2e                # live E2E (stack must be running)
  ```

---

## 🚀 Pull Request Checklist

Before submitting a Pull Request, ensure that:

- [ ] All new files and modules have thorough unit tests in their respective `tests/` folders.
- [ ] You have run `pre-commit run --all-files` and all lints/formatters pass cleanly.
- [ ] Local tests pass successfully (`uv run pytest` or `make check` for the full CI mirror).
- [ ] API schema changes: `make verify-openapi-sync` is clean and committed generated types are included.
- [ ] Metadata contract changes: golden/parity fixtures updated; [docs/chat-metadata.md](docs/chat-metadata.md) and docs site `/docs/execution-metadata` reviewed if user-facing.
- [ ] User-facing behavior: matching `apps/docs` page updated; [docs/README.md](docs/README.md) index checked if you added a new `docs/*.md` file.
- [ ] `make check-docs` and `make check-dashboard` pass when you touched docs site or dashboard.
- [ ] Multi-database or guardrails behavior: [docs/multi-database.md](docs/multi-database.md) / [docs/guardrails.md](docs/guardrails.md) and matching docs site pages updated.
- [ ] Embedder-facing changes: [docs/embedding.md](docs/embedding.md) and `/docs/embedding` reviewed.
- [ ] Production/deploy impact: [DEPLOYMENT.md](DEPLOYMENT.md) env or steps updated when operators need new config.
- [ ] Release-visible changes: note in PR for maintainers ([RELEASING.md](RELEASING.md) checklist before tag).
- [ ] Local planner eval changes: update `evals/data/eval_set.jsonl` / `docs/local-evals.md`; run `make eval-planner` locally when touching planner/SQL validation.
- [ ] You have documented your changes clearly in code comments and updated any relevant README guides.
