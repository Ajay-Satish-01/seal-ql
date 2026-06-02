# 🌌 Seal - AI Assistant Rules (GitHub Copilot)

Global rules for AI assistants working in the Seal codebase.

## 🏛️ Project Overview

AI-powered SQL generation, validation, and visualization with **schema-grounded chat Q&A**, a **global data catalog**, optional **vector RAG**, and **agent-compatible HTTP tools**.

## 🛠️ Tech Stack & Tooling

- **Python**: 3.11+ with `uv` workspaces
- **TypeScript**: `pnpm` for SDK, `apps/docs`, and `apps/web`
- **Backend**: FastAPI (`apps/api/`) — `/v1/query`, `/v1/chat`, `/v1/catalog`
- **Core**: LiteLLM + Instructor; chat in `packages/core/seal_core/chat/`; catalog in `catalog/`; enhancers in `enhancement/`; vectors in `vector/`
- **SQL**: SQLGlot (`packages/sql/`)
- **Databases**: Postgres (TimescaleDB), DuckDB
- **Lint**: `ruff`, `prettier`, `eslint`

## 📂 Architecture Mapping

| Path | Responsibility |
| ---- | -------------- |
| `apps/api/` | Routes, lifespan (catalog sync, enhancer chain, chat service) |
| `packages/core/seal_core/pipeline/` | Shared NL → SQL execution for query + chat |
| `packages/core/seal_core/chat/` | ChatService, sessions, streaming SSE |
| `packages/core/seal_core/catalog/` | YAML catalog sync + registry |
| `packages/core/seal_core/enhancement/` | PromptEnhancer orchestrator |
| `packages/core/seal_core/guardrails/` | Scope gate (heuristics + LLM) before SQL/RAG |
| `docs/README.md` | Index of all contributor markdown |
| `docs/embedding.md` | OSS embedder guide (boundaries, deployment, BFF) |
| `docs/how-seal-works.md` | Contributor pipeline + LLM stage reference |
| `DEPLOYMENT.md` / `CONTRIBUTORS.md` | Self-hosting and dev workflow |
| `packages/sql/` | AST validation |
| `packages/charts/` | Vega-Lite specs |
| `config/` | `catalog.example.yaml`, `seal-tools.openai.json`, `stream_meta_metadata_keys.json` |
| `shared/` | `stream-meta.ts`, `metadata-contract.ts`, `chat-sse-events.ts` (docs + dashboard; vendored into TS SDK) |
| `sdks/python`, `sdks/typescript` | Client SDKs (`typescript`: OpenAPI-generated `src/generated/openapi.ts`) |

## 📋 Standard Operating Procedures

### Python

- Use `uv run` for tests and tools (`uv run pytest -v`, `uv run ruff check .`)
- Add deps with `uv add` to the correct workspace package
- All LLM-generated SQL must pass `packages/sql/` validation

### TypeScript

- SDK: `cd sdks/typescript && pnpm install`
- After API schema changes: `make openapi-ts` then `make verify-openapi-sync`; commit `src/generated/openapi.ts` and OpenAPI copies
- Docs app: `make check-docs` or `cd apps/docs && pnpm build`
- Dashboard: `make check-dashboard` or `cd apps/web && pnpm build`

### Local services

- `make up` → API, Postgres, Ollama (if profile default)
- `make seed` → analytics seed schema
- `make sync-catalog` → refresh `config/catalog.yaml`

### Chat / catalog changes

- Preserve user descriptions on catalog re-sync (merge, do not overwrite `table_description`)
- Default `VECTOR_STORE=none`; Chroma only via optional extra
- Chat streaming: flat JSON in `seal.meta`, then token deltas, then `[DONE]`; invalid meta → client `meta_error` (see `docs/chat-metadata.md`)
- Execution metadata: keep Python `validate_metadata.py`, `config/stream_meta_metadata_keys.json`, and `shared/*` in sync

### Code generation rules

- **Safety**: Block destructive SQL; enforce LIMIT
- **Types**: Pydantic in `apps/api/app/schemas.py` → `make openapi` / `make openapi-ts`; do not hand-edit SDK `types.ts` field lists
- **Docs**: Update README, SETUP, DEPLOYMENT, AGENTS.md, `docs/*.md` (especially `docs/chat-metadata.md`), and `apps/docs` pages when adding API surface or metadata fields
