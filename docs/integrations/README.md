# Integrations

Contributor docs for extending Seal. User-facing copies live on the docs site (`apps/docs`, port 3000). Full tree index: [../README.md](../README.md).

| Doc | Topic | Docs site |
| --- | ----- | --------- |
| [embedding.md](../embedding.md) | OSS embedder guide — responsibilities, deployment, boundaries | `/docs/embedding` |
| [agent-frameworks.md](./agent-frameworks.md) | HTTP tools (`seal-tools.openai.json`), Mastra/LangChain patterns | `/docs/agent-frameworks` |
| [multi-database.md](../multi-database.md) | `database_id` routing, `DatabaseRegistry` | `/docs/multi-database` |
| [vector-stores.md](./vector-stores.md) | `VECTOR_STORE`, Chroma, custom `VECTOR_STORE_CLASS` | `/docs/vector-rag` |
| [custom-enhancers.md](./custom-enhancers.md) | `SEAL_ENHANCERS`, `PromptEnhancer` protocol | `/docs/prompt-enhancement` |

**Core behavior** (guardrails, LLM stages, SQL pipeline): [../how-seal-works.md](../how-seal-works.md).

Sync public assets: `make sync-docs-assets` (OpenAPI, demo fixtures, `seal-tools.openai.json`, catalog example).

When changing request/response models or tool manifests that affect the HTTP API, run `make openapi-ts` and `make verify-openapi-sync` before merge (see [../chat-metadata.md](../chat-metadata.md) for execution metadata fields).
