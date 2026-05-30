# 🌌 Seal - AI Assistant Rules (GitHub Copilot)

These are the global rules for AI assistants (Cursor, Claude, Windsurf, Copilot, Gemini) interacting with the Seal codebase.

## 🏛️ Project Overview
This project is an AI-powered SQL query generation, validation, and visualization SDK. It enables natural language querying over databases with client/server safety and native visual chart rendering.

## 🛠️ Tech Stack & Tooling
- **Python**: 3.11+ using `uv` for workspace and dependency management.
- **TypeScript**: Using `pnpm` for the TypeScript SDK.
- **Backend API**: FastAPI (located in `apps/api/`).
- **Core LLM Logic**: LiteLLM + Instructor + Ollama (located in `packages/core/`).
- **SQL Validation**: SQLGlot (located in `packages/sql/`).
- **Databases**: Postgres (TimescaleDB) and DuckDB.
- **Linting & Formatting**:
  - Python: `ruff`
  - TypeScript: `prettier` & `eslint`

## 📂 Architecture Mapping
- **`apps/api/`**: The FastAPI backend service.
- **`packages/core/`**: Core Models, Introspection & Planner.
- **`packages/sql/`**: Dialect Validators & AST Safety checkers.
- **`packages/charts/`**: Vega-Lite Spec Generators.
- **`packages/semantic/`**: Semantic metrics registries.
- **`sdks/python/`**: Python SDK wrapper.
- **`sdks/typescript/`**: TypeScript SDK wrapper.
- **`scripts/`**: Contains database seed scripts (`seed.sql`).

## 📋 Standard Operating Procedures

### 1. Modifying Python Code
- Always run commands via `uv`. E.g., `uv run pytest -v` or `uv run ruff check .`
- Ensure any new package dependencies are added using `uv add` to the correct workspace package.
- Respect the strict quality gate: run `pre-commit run --all-files` to ensure `ruff` formatting passes.

### 2. Modifying TypeScript Code
- Navigate to `sdks/typescript/` and use `pnpm` for all operations.
- Run `pnpm install` if dependencies are modified.
- Validate with `eslint` and `prettier`.

### 3. Running Services locally
- Instruct the user to run `make up` to spin up the API, Postgres, and Ollama containers via Docker Compose.
- If database schema testing is needed, mention `make seed` to populate TimescaleDB hypertables.

### 4. Code Generation Rules
- **Safety First**: Any dynamically generated SQL must pass through the `SQLGlot` AST validator to prevent destructive statements (`DROP`, `DELETE`, etc.).
- **Type Safety**: Maintain strict type hints in Python (Pydantic/Instructor) and TypeScript interfaces.
- **LLM Context**: When modifying LLM prompts, consider the context limits and keep instructions clear for the LiteLLM/Ollama integrations.
