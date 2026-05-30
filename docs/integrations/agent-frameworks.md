# Agent framework integration

Seal exposes HTTP tools compatible with OpenAI function-calling manifests:

- `config/seal-tools.openai.json` (copied to `apps/web/public/` on `make sync-docs-assets`)
- Tools: `seal_get_schema`, `seal_get_catalog`, `seal_query`, `seal_chat`

## Standalone vs framework-attached

| Mode | RAG / memory | Orchestration |
| ---- | ------------ | ------------- |
| Default Seal | Built-in enhancer chain + optional Chroma | Your app or SDK |
| Framework-attached | Framework and/or Seal | Mastra, LangGraph, etc. |

When your agent already has RAG, call `seal_query` / `seal_chat` with `enhancement: false` and `VECTOR_STORE=none`.

Manifest path in repo: `config/seal-tools.openai.json` (copied to `apps/web/public/` via `make sync-docs-assets`).
