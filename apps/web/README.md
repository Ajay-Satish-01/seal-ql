# Seal dashboard (`apps/web`)

Operational console for a running Seal API. Uses the TypeScript SDK against a live backend (no static demo fixtures).

## Pages

| Page         | Purpose                                                                                                                                                         |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Query**    | `POST /v1/query` with `database_id` — NL → SQL, results, Vega-Lite chart                                                                                        |
| **Chat**     | `POST /v1/chat` with SSE streaming; **Metadata** panel from flat `seal.meta` (badges via `shared/metadata-summary.ts`, including refusal + `suggested_queries`) |
| **Schema**   | `GET /v1/schema?database_id=…` — live DDL for the selected backend                                                                                              |
| **Catalog**  | `GET /v1/catalog`, description overrides via `PATCH /v1/catalog/descriptions` (default DB only; banner when another id is selected)                             |
| **Settings** | `GET` / `PATCH /v1/workspace/settings` (guardrails, enhancement, limits)                                                                                        |
| **Vector**   | `POST /v1/vector/reindex` when `VECTOR_STORE` is enabled (default DB only)                                                                                      |

Connection bar: API base URL (`http://localhost:8000`), `X-API-Key`, and **Database** dropdown (`database_id` on Query/Chat/Schema). Embedder guide: docs site `/docs/embedding` ([`docs/embedding.md`](../../docs/embedding.md)).

## Local dev

```bash
# API + Postgres (from repo root)
make up

# Docs site (port 3000) — separate terminal
cd apps/docs && pnpm install && pnpm dev

# Dashboard (port 3001)
cd apps/web && pnpm install && pnpm dev
```

| Service   | URL                   |
| --------- | --------------------- |
| API       | http://localhost:8000 |
| Docs      | http://localhost:3000 |
| Dashboard | http://localhost:3001 |

Set `CORS_ORIGINS` to include `http://localhost:3001` (default in repo `.env.example`).

Optional env for the dashboard app (`apps/web/.env.local`):

| Variable                      | Purpose                                                                                      |
| ----------------------------- | -------------------------------------------------------------------------------------------- |
| `NEXT_PUBLIC_DEFAULT_API_URL` | Default API URL in the connection bar (default `http://localhost:8000`)                      |
| `NEXT_PUBLIC_DOCS_URL`        | Base URL for sidebar help links (default `http://localhost:3000`; see `src/lib/docs-url.ts`) |

## Shared metadata modules

The dashboard imports `shared/stream-meta.ts`, `shared/chat-sse-events.ts`, `shared/metadata-contract.ts`, and `shared/api-error.ts` (same as `apps/docs`). Query/chat API errors use `formatApiError()` so structured guardrails 400s (`query_out_of_scope` + `suggested_queries`) and session mismatch messages render readably in the UI. Invalid `seal.meta` payloads (including unknown `scope.source` or enhancement reason strings) surface as `meta_error` while preserving partial `session_id` / `database_id` when present.

| UI                   | Data                                                                     |
| -------------------- | ------------------------------------------------------------------------ |
| **Query** (`/query`) | `response.metadata` (`QueryMetadata` from OpenAPI)                       |
| **Chat** (`/chat`)   | Flat fields from first SSE `seal.meta`; badges via `metadata-summary.ts` |

Allowed `metadata.scope.source` values: `heuristic`, `llm`, `limits`, `disabled`. On guardrails refusal, `metadata.suggested_queries` lists up to three example in-scope questions (also on flat `seal.meta`). Field reference: [docs/chat-metadata.md](../../docs/chat-metadata.md) and docs site `/docs/execution-metadata`, `/docs/guardrails`.

## Build

```bash
make check-dashboard
```
