# Seal dashboard (`apps/web`)

Operational console for a running Seal API. Uses the TypeScript SDK against a live backend (no static demo fixtures).

## Pages

| Page | Purpose |
|------|---------|
| **Query** | `POST /v1/query` — natural language → SQL, results, Vega-Lite chart |
| **Chat** | `POST /v1/chat` with SSE streaming |
| **Catalog** | `GET /v1/catalog`, description overrides via `PATCH /v1/catalog/descriptions` |
| **Settings** | `GET` / `PATCH /v1/workspace/settings` (guardrails, enhancement, limits) |
| **Vector** | `POST /v1/vector/reindex` when `VECTOR_STORE` is enabled |

Connection bar: API base URL (`http://localhost:8000`) and `X-API-Key`.

## Local dev

```bash
# API + Postgres (from repo root)
make up

# Docs site (port 3000) — separate terminal
cd apps/docs && pnpm install && pnpm dev

# Dashboard (port 3001)
cd apps/web && pnpm install && pnpm dev
```

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Docs | http://localhost:3000 |
| Dashboard | http://localhost:3001 |

Set `CORS_ORIGINS` to include `http://localhost:3001` (default in `.env.example`).

## Build

```bash
make check-dashboard
```
