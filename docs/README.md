# Contributor documentation (`docs/`)

Markdown in this directory describes **how Seal works** for contributors and integrators. User-facing copies of most topics live on the docs site (`apps/docs`, port **3000**) under `/docs/*`.

**Root guides:** [CONTRIBUTORS.md](../CONTRIBUTORS.md) (dev workflow) · [DEPLOYMENT.md](../DEPLOYMENT.md) (self-hosting) · [RELEASING.md](../RELEASING.md) (version bump & publish) · [SETUP.md](../SETUP.md) (quick reference) · [AGENTS.md](../AGENTS.md) (AI assistant rules)

## Start here

| If you are… | Read |
| ----------- | ---- |
| Embedding Seal in your product or agent | [embedding.md](embedding.md) → docs site [`/docs/embedding`](http://localhost:3000/docs/embedding) |
| Changing query/chat pipeline or LLM stages | [how-seal-works.md](how-seal-works.md) → `/docs/how-it-works` |
| Wiring multiple SQL backends | [multi-database.md](multi-database.md) → `/docs/multi-database` |
| Changing metadata on responses or SSE | [chat-metadata.md](chat-metadata.md) → `/docs/execution-metadata` |
| Deploying Docker / production | [../DEPLOYMENT.md](../DEPLOYMENT.md) → `/docs/self-hosting` |
| Cutting a release | [../RELEASING.md](../RELEASING.md) (no docs site page — repo-only) |

## Core pipeline

| Doc | Topic | Docs site |
| --- | ----- | --------- |
| [how-seal-works.md](how-seal-works.md) | Query vs chat flow, guardrails, enhancement, shared SQL pipeline | `/docs/how-it-works` |
| [guardrails.md](guardrails.md) | Scope gate, refusals, `suggested_queries`, query 400 shape | `/docs/guardrails` |
| [zero-trust-sql.md](zero-trust-sql.md) | SQLGlot validator, sanitizer, LIMIT policy | `/docs/zero-trust-sql` |
| [chat-enhancement.md](chat-enhancement.md) | Enhancer chain, `SEAL_ENHANCERS` | `/docs/prompt-enhancement` |
| [chat-metadata.md](chat-metadata.md) | `ExecutionMetadata`, JSON vs SSE `seal.meta` | `/docs/execution-metadata` |

## Configuration & data

| Doc | Topic | Docs site |
| --- | ----- | --------- |
| [multi-database.md](multi-database.md) | `database_id`, `DatabaseRegistry`, session pinning | `/docs/multi-database` |
| [workspace-api.md](workspace-api.md) | Postgres workspace KV, hot-reload, catalog overrides | `/docs/workspace` |
| Env tables (user-facing) | — | `/docs/configuration` |

## Integrations (`docs/integrations/`)

| Doc | Topic | Docs site |
| --- | ----- | --------- |
| [integrations/README.md](integrations/README.md) | Index of extension docs | — |
| [integrations/agent-frameworks.md](integrations/agent-frameworks.md) | `seal-tools.openai.json`, tool errors | `/docs/agent-frameworks` |
| [integrations/vector-stores.md](integrations/vector-stores.md) | Chroma, `VECTOR_STORE_CLASS` | `/docs/vector-rag` |
| [integrations/custom-enhancers.md](integrations/custom-enhancers.md) | Custom `PromptEnhancer` | `/docs/prompt-enhancement` |

## Embedding & boundaries

| Doc | Topic | Docs site |
| --- | ----- | --------- |
| [embedding.md](embedding.md) | Your app vs Seal, deployment patterns, scope → SQL → RAG | `/docs/embedding` |

## Apps & assets

| Path | Role |
| ---- | ---- |
| `apps/docs/` | Public docs + `/demo` fixtures — [apps/docs/README.md](../apps/docs/README.md) |
| `apps/web/` | Live API console (port **3001**) — [apps/web/README.md](../apps/web/README.md) |
| `config/` | `catalog.example.yaml`, `databases.example.yaml`, `seal-tools.openai.json` |
| `shared/` | Stream-meta contract for docs + dashboard — [shared/README.md](../shared/README.md) |

## Keeping docs in sync

| Change | Action |
| ------ | ------ |
| API request/response models | `make openapi-ts` · `make verify-openapi-sync` |
| Demo fixtures / public OpenAPI copy | `make sync-docs-assets` |
| Metadata keys | `config/stream_meta_metadata_keys.json` + golden fixtures (see [chat-metadata.md](chat-metadata.md)) |
| User-facing prose | Update matching `apps/docs/src/app/docs/*/page.tsx` and this tree |

```bash
make check-docs       # Next.js docs build
make check-dashboard  # Dashboard build
make check            # Full CI mirror (includes above)
```
