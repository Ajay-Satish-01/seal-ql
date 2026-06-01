# Agent framework integration

Seal exposes HTTP tools compatible with OpenAI function-calling manifests:

- `config/seal-tools.openai.json` (copied to `apps/docs/public/` on `make sync-docs-assets`)
- Tools: `seal_get_schema`, `seal_get_catalog`, `seal_query`, `seal_chat`

## Standalone vs framework-attached

| Mode | RAG / memory | Orchestration | When to use |
| ---- | ------------ | ------------- | ----------- |
| Default Seal | Built-in enhancer chain + optional Chroma | Your app or SDK | You want schema + catalog + optional vector RAG without building tools |
| Framework-attached | Framework and/or Seal | Mastra, LangGraph, etc. | Agent already has memory/RAG; Seal as SQL + chart tool |

When your agent already has RAG, call `seal_query` / `seal_chat` with **`enhancement: false`** and keep **`VECTOR_STORE=none`** to avoid duplicate context injection.

## What to expect per tool

| Tool | Behavior |
|------|----------|
| `seal_get_schema` | Live DDL introspection JSON for `database_id` — no LLM |
| `seal_get_catalog` | Global catalog YAML as JSON — no LLM |
| `seal_query` | Guardrails → planner → SQL → chart; `database_id` selects backend |
| `seal_chat` | Session + guardrails + enhancement + optional SQL; `database_id` on each turn |

Pass `X-API-Key` when `SEAL_API_KEY` is set. Use a backend proxy — do not embed production keys in browser agents.

Register additional backends with `SEAL_DATABASES_PATH` or `SEAL_DATABASES`; pass `database_id` on tools that accept it. See [../multi-database.md](../multi-database.md).

### `database_id` per tool

| Tool | `database_id` | Notes |
| ---- | ------------- | ----- |
| `seal_get_schema` | Optional (default `default`) | Live DDL for that backend |
| `seal_get_catalog` | N/A | Global catalog from default DB sync |
| `seal_query` | Optional (default `default`) | Unknown id → HTTP 404 before guardrails |
| `seal_chat` | Optional (default `default`) | Pass on **every** turn; session pins after first successful in-scope reply |

DuckDB entries use `duckdb:///path/file.duckdb` or `:memory:` in config (see multi-database guide).

## Scope and errors

- Unknown `database_id`: HTTP 404 `unknown_database_id`
- Chat session id mismatch: HTTP 400 `session_database_id_mismatch` (structured `detail.code`)
- Query off-topic: HTTP 400 `query_out_of_scope` (see [../guardrails.md](../guardrails.md))
- Chat off-topic: HTTP 200 with `metadata.scope.in_scope: false` and `metadata.database_id` set

Full pipeline: [../how-seal-works.md](../how-seal-works.md).

User-facing: `/docs/agent-frameworks` on the docs site.
