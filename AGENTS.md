# AGENTS.md

## Repository Structure

- `apps/api/`: FastAPI backend service (`/v1/query`, `/v1/chat`, `/v1/catalog`)
- `apps/web/`: Docs site, marketing, interactive demo (`/demo` with query + chat)
- `packages/core/`: Planner, introspection, **chat**, **catalog**, **enhancement**, **vector** RAG, shared **pipeline**
- `packages/sql/`: Dialect validators & AST safety checkers
- `packages/charts/`: Vega-Lite spec generators
- `packages/semantic/`: Semantic metrics registries
- `sdks/python/`, `sdks/typescript/`: SDK wrappers (`query`, `chat`, `chatStream`, `catalog`)
- `config/`: `catalog.example.yaml`, `seal-tools.openai.json`
- `scripts/`: `seed.sql`, `sync_catalog.py`
- `docs/`: Contributor docs (`chat-enhancement.md`, `integrations/`)

## Architecture

- **API Gateway**: FastAPI; routes NL requests to query or chat paths.
- **Data catalog**: Auto-synced global YAML (`DATA_CATALOG_PATH`); feeds planner + `SchemaAwareEnhancer`.
- **Chat**: `ChatService` + `SessionStore` + `EnhancementOrchestrator` (schema → vector RAG → multi-turn).
- **Query Planner**: LiteLLM + Instructor; shared `execute_natural_language_query` pipeline with chat SQL.
- **SQL Validator**: SQLGlot AST — zero-trust boundary for all LLM-generated SQL.
- **Database Executor**: Postgres (TimescaleDB) or DuckDB.
- **Chart Spec Generator**: Vega-Lite; always on `/v1/query`; optional on chat via `include_charts`.

## Docker

- Docker-first: image `seal/api` on Docker Hub; compose stacks API + Postgres + optional Ollama.
- Mount `./config` for catalog YAML persistence (`CATALOG_AUTO_SYNC`, `DATA_CATALOG_PATH`).
- Default `VECTOR_STORE=none`; optional Chroma via `seal-core[chroma]` and `VECTOR_STORE=chroma`.

## SDKs

- Python and TypeScript: `Seal` / `AsyncSeal` with `query`, `schema`, `catalog`, `chat`, `chat_stream` / `chatStream`.
- Pass `api_key` / `apiKey` when `SEAL_API_KEY` is set (`X-API-Key`).
- LiteLLM for providers (OpenAI, Anthropic, Google, Ollama, etc.); Postgres and DuckDB for data.

## Conventions

- Python: `uv` workspaces; Pydantic + Instructor for structured LLM outputs.
- TypeScript: `pnpm`; Vega-Lite chart objects from API.
- Fast, safe SQL over long multi-turn planner loops in a single HTTP request.

## Commands

- `make up` / `make down` / `make seed`: Docker stack and seed data.
- `make sync-catalog`: Regenerate `config/catalog.yaml` from live schema.
- `make sync-docs-assets`: OpenAPI + demo fixtures + `seal-tools.openai.json` → `apps/web`.
- `make verify-openapi-sync`: CI check for committed OpenAPI copies.
- `make validate-query`: Live `POST /v1/query` shape check (API running).
- `make check-web`: Build TS SDK + Next.js docs app.
- `uv sync --all-packages --all-extras` / `uv run pytest -v`
- `pre-commit run --all-files`

## Workflows

- **Schema / catalog**: Introspection in `packages/core/`; catalog sync preserves user `table_description` / `view_description`.
- **Chat / enhancement**: Changes in `seal_core/enhancement/` and `seal_core/chat/`; wire default chain in `apps/api` lifespan.
- **Agent queries**: All dynamic SQL through `packages/sql/` AST validation — never execute raw LLM SQL.
- **Visualization**: Chart columns must match SQL result columns.

## Generation Rules

- **Zero-Trust**: SQLGlot parse required for every generated statement.
- **No destructive ops**: `DROP`, `DELETE`, `TRUNCATE`; enforce `LIMIT` on selects.
- **Model output**: Instructor for structured planner/chat decisions.

## Testing

- API tests: `apps/api/tests/` (`test_chat.py`, `test_chat_stream.py`, mocks in `factory.py`).
- Core: `packages/core/tests/` (catalog, enhancement, vector, pipeline).
- SDK: `sdks/python/tests/test_chat_client.py`; `tests/test_seal_tools_manifest.py`.
- Run: `uv run pytest -v` in the uv virtualenv.

## Release Process

See `RELEASING.md` and `SETUP.md`. Bump aligned versions in API + both SDKs; `make check`; tag `v*.*.*`.

## Invariants

- Never bypass `packages/sql/` AST parser.
- Never hardcode LLM provider — use LiteLLM.
- Catalog is **global** (not per-request): same registry for `/v1/query` and `/v1/chat`.
