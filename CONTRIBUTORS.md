# 👥 Contributors & Developer Guide

Thank you for contributing to the **Intelligence Connector**! This document outlines our repository architecture, coding guidelines, development workflow, and the processes we use to write, test, and merge code.

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
git clone https://github.com/Ajay-Satish-01/intelligence.git
cd intelligence_connector

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
