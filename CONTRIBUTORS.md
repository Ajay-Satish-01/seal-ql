# 👥 Contributors & Developer Guide

Thank you for contributing to the **Seal**! This document outlines our repository architecture, coding guidelines, development workflow, and the processes we use to write, test, and merge code.

---

## 🏛️ Codebase Structure

We use a monorepo architecture managed by modern tooling:

* **Backend (Python)**: Configured as a unified `uv` workspace. The workspace root `pyproject.toml` references:
  * `apps/api` (FastAPI app container)
  * `packages/core` (Planner, chat, catalog, enhancement, guardrails, workspace, vector RAG, introspection)
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
cd apps/web && pnpm dev   # when dashboard package.json exists
```

### 3. Pre-commit & Push Hook Installation
```bash
# Install local validation hooks
make setup
```

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
2. **Work Locally**: Build your changes, keeping commits granular and descriptive.
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
* **Linter**: [ESLint](https://eslint.org/) (Flat Config v9+) using the TypeScript ESLint extension rules.
* **Directory Scope**: Scoped to the `sdks/typescript/` folder.
* **Manual execution** (within `sdks/typescript/`):
  ```bash
  pnpm run lint     # Run eslint checks
  pnpm run format   # Reformat code with prettier
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
  2. The `QueryPlanner` automatically injects these business metrics and definitions into the system prompt context.
  3. The LLM can then reason over logical business concepts ("Revenue", "Active Users") rather than raw columns, significantly improving generation accuracy.

### 🔄 Repair Loops
**Purpose**: To gracefully recover from LLM hallucinations or SQL Dialect syntax errors without failing the user's request.
- **Workflow**:
  1. When the `QueryPlanner` generates SQL, it immediately passes through the strict `SQLValidator` and `SQLSanitizer`.
  2. If the query is destructive (e.g., contains `DROP` or `DELETE`), uses non-existent columns, or fails execution on the underlying database (e.g., `DuckDB` or `TimescaleDB`), an error is raised.
  3. The API execution route catches these errors and triggers the `QueryPlanner.repair_plan` method.
  4. The LLM is provided with its original failed query and the exact database/validator error message, and is prompted to fix the mistake. This loop can retry up to a configurable number of attempts (e.g., 3).

### 🧪 Evaluations (Evals)
**Purpose**: To rigorously track and measure the accuracy, safety, and repair-ability of the Query Planner.
- Located in `evals/`, the eval suite acts as an automated grading system for the LLM.
- **`eval_set.jsonl`**: A dataset containing natural language questions, expected outcomes, and expected schema targets.
- **`EvalRunner`**: Connects to the database (either DuckDB or Postgres) and evaluates the planner against the dataset. It tracks `execution_success`, `validation_success`, and how many queries successfully recovered via the `repair_loop`.
- To run evals:
  ```bash
  # DuckDB in-memory evaluation
  uv run python evals/seal_evals/runner.py :memory:

  # TimescaleDB/Postgres evaluation (in docker)
  docker compose exec api uv run python evals/seal_evals/runner.py postgresql+asyncpg://postgres:postgres@postgres:5432/seal
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

## 🧪 Testing Guidelines

No code should be pushed or merged without comprehensive test coverage.

### 🐍 Python Tests
Python tests are written using `pytest` and `pytest-asyncio` for async database handlers.

* **Locating tests**: Add test modules under `tests/` directories in respective packages (e.g. `packages/core/tests/test_schema.py`).
* **Test Database**: Docker containers run a dedicated `postgres` database seeded with the standard schemas. Mocking is encouraged for LLM/Ollama providers, while actual database execution is run against test instances.
* **Executing tests**:
  ```bash
  # Run all tests locally in virtual env
  uv run pytest -v

  # Run all tests using docker container
  make test

  # Run tests with HTML coverage report
  make test-cov
  ```

---

## 🚀 Pull Request Checklist

Before submitting a Pull Request, ensure that:

- [ ] All new files and modules have thorough unit tests in their respective `tests/` folders.
- [ ] You have run `pre-commit run --all-files` and all lints/formatters pass cleanly.
- [ ] Local tests pass successfully (`uv run pytest` or `make check` for the full CI mirror).
- [ ] API schema changes: `make verify-openapi-sync` is clean and committed generated types are included.
- [ ] Metadata contract changes: golden/parity fixtures updated; [docs/chat-metadata.md](docs/chat-metadata.md) and docs site `/docs/execution-metadata` reviewed if user-facing.
- [ ] You have documented your changes clearly in code comments and updated any relevant README guides.
