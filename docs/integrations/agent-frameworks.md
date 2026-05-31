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
| `seal_get_schema` | Live DDL introspection JSON — no LLM |
| `seal_get_catalog` | Global catalog YAML as JSON — no LLM |
| `seal_query` | Guardrails → planner → SQL → chart; out-of-scope → error |
| `seal_chat` | Session + guardrails + enhancement + optional SQL; out-of-scope → 200 refusal |

Pass `X-API-Key` when `SEAL_API_KEY` is set. Use a backend proxy — do not embed production keys in browser agents.

## Scope and errors

- Query off-topic: HTTP 400 `query_out_of_scope` (see [../guardrails.md](../guardrails.md))
- Chat off-topic: HTTP 200 with `metadata.scope.in_scope: false`

Full pipeline: [../how-seal-works.md](../how-seal-works.md).

User-facing: `/docs/agent-frameworks` on the docs site.
