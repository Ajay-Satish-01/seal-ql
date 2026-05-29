---
name: local-dev-workflow
description: Step-by-step workflow for spinning up the local environment, seeding the database, and running tests.
---

# Spin Up Local Environment and Test

1. **Start Docker Services**
   Run `make up`. Wait for the Postgres, FastAPI, and Ollama containers to report healthy.

2. **Seed the Database**
   Run `make seed`. This creates the mock TimescaleDB hypertables and continuous aggregates needed for AST testing.

3. **Install Dependencies**
   Run `uv sync --all-packages --all-extras` to ensure the Python workspaces are fully linked.
   Run `cd sdks/typescript && pnpm install` to prepare the frontend SDK.

4. **Run Validations**
   Run `pre-commit run --all-files` to format and lint the code.

5. **Run Test Suite**
   Run `uv run pytest -v` from the project root. Ensure all AST safety checks pass.
