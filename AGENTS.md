# AGENTS.md

## Repository Structure

- `apps/api/`: FastAPI backend (`/v1/query`, `/v1/chat`, `/v1/catalog`, workspace, vector)
- `apps/docs/`: Docs site, marketing, fixture-based `/demo` (Next.js, port **3000**)
- `apps/web/`: Operational dashboard — live API console (Next.js, port **3001**)
- `packages/core/`: Planner, introspection, **chat**, **catalog**, **enhancement**, **guardrails**, **vector** RAG, **workspace**, shared **pipeline**
- `packages/sql/`: Dialect validators & AST safety checkers
- `packages/charts/`: Vega-Lite spec generators
- `packages/semantic/`: Semantic metrics registries
- `sdks/python/`, `sdks/typescript/`: SDK wrappers (`query`, `chat`, `chatStream`, `catalog`)
- `config/`: `catalog.example.yaml`, `seal-tools.openai.json`, `stream_meta_metadata_keys.json`
- `scripts/`: `seed.sql`, `migrate_app.sql`, `sync_catalog.py`, `generate_openapi.py`
- `evals/`: `seal_evals/runner.py`, `data/eval_set.jsonl` — planner eval harness
- `docs/`: Contributor docs — **index:** [docs/README.md](docs/README.md) (`embedding.md`, `how-seal-works.md`, `multi-database.md`, `guardrails.md`, `chat-enhancement.md`, `chat-metadata.md`, `workspace-api.md`, `integrations/`)
- `shared/`: Cross-app TypeScript (`stream-meta.ts`, `metadata-contract.ts`, `metadata-summary.ts`) for docs + dashboard

## Architecture

- **API Gateway**: FastAPI; scope gate on query/chat; routes NL requests to planner or chat.
- **Guardrails**: Heuristics + LLM `ScopeDecision` before SQL/RAG; chat refusal vs query 400.
- **Data catalog**: Auto-synced YAML (`DATA_CATALOG_PATH`); description overrides in workspace DB (re-applied after sync).
- **Chat**: `ChatService` + `SessionStore` + `EnhancementOrchestrator` (schema → vector RAG → multi-turn).
- **Workspace**: Postgres `seal_app.workspace_kv` (primary); `config/workspace.json` read fallback; `.env` base. Hot-reload on save in dev; prod uses `POST /v1/workspace/settings/apply`.
- **Query Planner**: LiteLLM + Instructor; shared `execute_natural_language_query` pipeline with chat SQL.
- **SQL Validator**: SQLGlot AST — zero-trust boundary for all LLM-generated SQL.
- **Database Executor**: Postgres (TimescaleDB) or DuckDB.
- **Chart Spec Generator**: Vega-Lite; always on `/v1/query`; optional on chat via `include_charts`.

## Docker

- Docker-first: image `seal/api` on Docker Hub; compose stacks API + Postgres + optional Ollama.
- Mount `./config` for catalog YAML persistence (`CATALOG_AUTO_SYNC`, `DATA_CATALOG_PATH`).
- Default `VECTOR_STORE=none`; optional Chroma via `seal-core[chroma]` and `VECTOR_STORE=chroma`.
- Local frontends: docs **3000**, dashboard **3001**, API **8000**.

## SDKs

- Python and TypeScript: `Seal` / `AsyncSeal` with `query`, `schema`, `catalog`, `chat`, `chat_stream` / `chatStream`.
- **TypeScript types**: Pydantic v2 → FastAPI OpenAPI (`make openapi`) → `openapi-typescript` (`make openapi-ts`) → `sdks/typescript/src/generated/openapi.ts`. Do not edit `types.ts` field lists by hand; regenerate.
- Pass `api_key` / `apiKey` when `SEAL_API_KEY` is set (`X-API-Key`).
- LiteLLM for providers (OpenAI, Anthropic, Google, Ollama, etc.); Postgres and DuckDB for data.

## Conventions

- Python: `uv` workspaces; Pydantic + Instructor for structured LLM outputs.
- TypeScript: `pnpm`; Vega-Lite chart objects from API.
- Fast, safe SQL over long multi-turn planner loops in a single HTTP request.

## Commands

- `make up` / `make down` / `make seed`: Docker stack and seed data (`migrate_app.sql` for workspace).
- `make eval` / `make eval-planner` / `make eval-local`: **Local only** planner evals — see `docs/local-evals.md` (not in PR CI; requires LLM + seeded Postgres for full execution).
- `make sync-catalog`: Regenerate `config/catalog.yaml` from live schema.
- `make sync-docs-assets`: OpenAPI + demo fixtures → `apps/docs`.
- `make verify-openapi-sync`: CI check for committed OpenAPI spec, docs copies, and `sdks/typescript/src/generated/openapi.ts`.
- `make check-docs` / `make check-dashboard` / `make check-web`: Build docs and dashboard apps.
- `uv sync --all-packages --all-extras` / `uv run pytest -v`
- `pre-commit run --all-files`

## Workflows

- **Schema / catalog**: Introspection in `packages/core/`; catalog sync preserves user descriptions; PATCH `/v1/catalog/descriptions` for overrides.
- **Guardrails**: `packages/core/seal_core/guardrails/`; wire in `ChatService` and `apps/api` query route.
- **Chat / enhancement**: Changes in `seal_core/enhancement/` and `seal_core/chat/`; wire default chain in `apps/api` lifespan.
- **Workspace**: `seal_core/workspace/` + `apps/api/app/routes/workspace.py`; startup + hot-reload via `apply_workspace_on_startup` / `apply_runtime_overrides`.
- **Agent queries**: All dynamic SQL through `packages/sql/` AST validation — never execute raw LLM SQL.
- **Visualization**: Chart columns must match SQL result columns.
- **Execution metadata**: `packages/core/seal_core/pipeline/validate_metadata.py` + `config/stream_meta_metadata_keys.json`; shared TS in `shared/`; contributor doc `docs/chat-metadata.md`.
- **OpenAPI / SDK types**: Edit `apps/api/app/schemas.py` → `make openapi-ts` → commit spec + `sdks/typescript/src/generated/openapi.ts`; `scripts/generate_openapi.py` injects SSE-only models (e.g. `ChatStreamMeta`).

## Generation Rules

- **Zero-Trust**: SQLGlot parse required for every generated statement.
- **No destructive ops**: `DROP`, `DELETE`, `TRUNCATE`; enforce `LIMIT` on selects.
- **Model output**: Instructor for structured planner/chat/guardrails decisions.

## Testing

- API tests: `apps/api/tests/` (`test_chat.py`, `test_workspace.py`, mocks in `factory.py`).
- Core: `packages/core/tests/` (catalog, enhancement, vector, guardrails, workspace, `test_validate_metadata.py`, `test_chat_flatten_contract.py`, stream-meta parity).
- SDK: `sdks/python/tests/test_chat_client.py`; `sdks/typescript` Vitest; `tests/test_seal_tools_manifest.py`.
- Metadata contract: `tests/fixtures/chat_flatten_golden.json`, `tests/fixtures/stream_meta_validation_matrix.json`; `make check` runs flatten + parity scripts.
- Run: `uv run pytest -v` in the uv virtualenv; `make check` before merge.

## Release Process

See `RELEASING.md` and `SETUP.md`. Bump aligned versions in API + both SDKs; `make check`; tag `v*.*.*`.

## Invariants

- Never bypass `packages/sql/` AST parser.
- Never hardcode LLM provider — use LiteLLM.
- Catalog is **global** (not per-request): same registry for `/v1/query` and `/v1/chat`.
- Out-of-scope chat returns 200 refusal with `metadata.suggested_queries`; out-of-scope query returns 400 structured `detail` (`query_out_of_scope`, `reason`, `suggested_queries`).
