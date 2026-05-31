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
| `docs/how-seal-works.md` | Contributor pipeline + LLM stage reference |
| `packages/sql/` | AST validation |
| `packages/charts/` | Vega-Lite specs |
| `config/` | `catalog.example.yaml`, `seal-tools.openai.json` |
| `sdks/python`, `sdks/typescript` | Client SDKs |

## 📋 Standard Operating Procedures

### Python

- Use `uv run` for tests and tools (`uv run pytest -v`, `uv run ruff check .`)
- Add deps with `uv add` to the correct workspace package
- All LLM-generated SQL must pass `packages/sql/` validation

### TypeScript

- SDK: `cd sdks/typescript && pnpm install`
- Docs app: `make check-docs` or `cd apps/docs && pnpm build`
- Dashboard: `make check-dashboard` or `cd apps/web && pnpm build`

### Local services

- `make up` → API, Postgres, Ollama (if profile default)
- `make seed` → analytics seed schema
- `make sync-catalog` → refresh `config/catalog.yaml`

### Chat / catalog changes

- Preserve user descriptions on catalog re-sync (merge, do not overwrite `table_description`)
- Default `VECTOR_STORE=none`; Chroma only via optional extra
- Chat streaming: `seal.meta` event then OpenAI-style chunks, then `[DONE]`

### Code generation rules

- **Safety**: Block destructive SQL; enforce LIMIT
- **Types**: Pydantic + strict Python hints; TS types mirror OpenAPI
- **Docs**: Update README, SETUP, DEPLOYMENT, AGENTS.md, `docs/*.md`, and `apps/docs` pages when adding API surface
