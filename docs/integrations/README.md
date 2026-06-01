# Integrations

Contributor docs for extending Seal. User-facing copies live on the docs site (`apps/docs`, port 3000).

| Doc | Topic | Docs site |
| --- | ----- | --------- |
| [agent-frameworks.md](./agent-frameworks.md) | HTTP tools (`seal-tools.openai.json`), Mastra/LangChain patterns | `/docs/agent-frameworks` |
| [multi-database.md](../multi-database.md) | `database_id` routing, `DatabaseRegistry` | `/docs/multi-database` |
| [vector-stores.md](./vector-stores.md) | `VECTOR_STORE`, Chroma, custom `VECTOR_STORE_CLASS` | `/docs/vector-rag` |
| [custom-enhancers.md](./custom-enhancers.md) | `SEAL_ENHANCERS`, `PromptEnhancer` protocol | `/docs/prompt-enhancement` |

**Core behavior** (guardrails, LLM stages, SQL pipeline): [../how-seal-works.md](../how-seal-works.md).

Sync public assets: `make sync-docs-assets` (OpenAPI, demo fixtures, `seal-tools.openai.json`, catalog example).
