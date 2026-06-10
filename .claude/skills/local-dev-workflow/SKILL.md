---
name: local-dev-workflow
description: Step-by-step workflow for spinning up the local environment, seeding the database, and running tests.
---

# Spin Up Local Environment and Test

1. **Start Docker Services**
   Run `make up`. Wait for Postgres, FastAPI, and Ollama (when `OLLAMA_PROFILE` is default) to be healthy.

2. **Seed the Database**
   Run `make seed`. Creates TimescaleDB hypertables and continuous aggregates for introspection and tests.
   Workspace and chat session schema (`scripts/migrate_app.sql`) are applied when the API starts — no manual migrate after `make up`.

3. **Sync Data Catalog (optional)**
   Run `make sync-catalog` or rely on `CATALOG_AUTO_SYNC=true` on API startup. Edit `config/catalog.yaml` descriptions for better chat/query answers.

4. **Install Dependencies**
   - `uv sync --all-packages --all-extras`
   - `cd sdks/typescript && pnpm install`

5. **Run Validations**
   - `pre-commit run --all-files`
   - If you changed `apps/api/app/schemas.py` or metadata fields: `make openapi-ts` and `make verify-openapi-sync`

6. **Run Test Suite**
   - `uv run pytest -v` (or `make check` for the full CI mirror including metadata contract scripts)

6b. **Local planner evals (optional, not in CI; requires LLM)**
   - See `docs/local-evals.md` — after `make up && make seed`
   - `make eval-planner` — validation-only against `evals/data/eval_set.jsonl`
   - `make eval` — full plan → validate → execute on seeded Postgres

7. **Smoke-test chat (API running, key from `.env`)**
   ```bash
   curl -s -X POST http://localhost:8000/v1/chat \
     -H "Content-Type: application/json" \
     -H "X-API-Key: $SEAL_API_KEY" \
     -d '{"message":"What tables exist?"}'
   ```

8. **Docs site (port 3000)**
   - `make sync-docs-assets`
   - `cd apps/docs && pnpm dev` → http://localhost:3000/docs/chat-qa

9. **Dashboard (port 3001, optional)**
   - `cd apps/web && pnpm dev` → http://localhost:3001 (live API console)
