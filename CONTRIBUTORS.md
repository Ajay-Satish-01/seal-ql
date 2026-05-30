# 👥 Contributors & Developer Guide

Thank you for contributing to the **Seal**! This document outlines our repository architecture, coding guidelines, development workflow, and the processes we use to write, test, and merge code.

---

## 🏛️ Codebase Structure

We use a monorepo architecture managed by modern tooling:

* **Backend (Python)**: Configured as a unified `uv` workspace. The workspace root `pyproject.toml` references:
  * `apps/api` (FastAPI app container)
  * `packages/core` (Schema schemas & introspectors)
  * `packages/sql` (AST-based SQL validators)
  * `packages/charts` (Vega-Lite visual generators)
  * `packages/semantic` (Metrics semantic compiler)
  * `sdks/python` (Python SDK wrapper)
  * `evals` (Testing datasets & repair evaluations)
* **Frontend/SDK (TypeScript)**: Configured under `sdks/typescript/` as an independent TypeScript package managed by `pnpm`.

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
- [ ] Local tests pass successfully (`uv run pytest`).
- [ ] You have documented your changes clearly in code comments and updated any relevant README guides.
