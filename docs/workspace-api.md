# Workspace API

Dashboard and API workspace state uses a **three-layer model**:

1. **Postgres (primary)** — `seal_app.workspace_kv` (`workspace_settings`, `catalog_overrides` JSON keys). All dashboard **writes** go here when the database is reachable.
2. **File (read fallback)** — `config/workspace.json` next to the data catalog. Used when Postgres has no row yet or is unavailable (local dev without DB).
3. **Environment (base)** — `.env` / process env via `Settings`. Any key not stored in Postgres or file uses these defaults.

```text
Effective value = .env defaults  ←  file overrides (if DB empty)  ←  Postgres overrides (if present)
```

Catalog **structure** still comes from auto-synced `config/catalog.yaml` (regenerated from live schema). **Description overrides** from the dashboard live in Postgres; after `POST /v1/catalog/sync`, YAML is rebuilt from the database and DB description overrides are re-applied to the in-memory catalog.

**User-facing guide:** `/docs/workspace` · **Env reference:** `/docs/configuration` on the docs site.

## Routes

| Method | Path | Purpose | What to expect |
|--------|------|---------|----------------|
| `GET` | `/v1/workspace/settings` | Effective settings + schema + storage | `effective`, `schema`, `storage.pending_apply` / `restart_required` |
| `PATCH` | `/v1/workspace/settings` | Update settings object | Dev: hot keys apply immediately; prod: may need apply |
| `POST` | `/v1/workspace/settings/apply` | Apply hot-reload keys (production) | Running API picks up guardrails, limits, `llm_model`, etc. |
| `GET` | `/v1/workspace/export` | Backup JSON | Settings + catalog description overrides |
| `PATCH` | `/v1/catalog/descriptions` | Table/view descriptions | Persisted in workspace; survive catalog sync |
| `POST` | `/v1/vector/reindex` | Rebuild vector index | Required after enabling Chroma or large catalog changes |

All routes require `X-API-Key` when `SEAL_API_KEY` is set.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `WORKSPACE_STORE` | `postgres` | `postgres` = DB primary + file read fallback; `file` = file-only (tests) |
| `DATABASE_URL` | Postgres URL | Required for primary storage |
| `SEAL_DEV_MODE` | `true` (local) | Hot-apply on PATCH vs persist-only + apply endpoint |

Schema: `scripts/migrate_app.sql` (`seal_app.workspace_kv`) — applied on API startup when using Postgres (`make seed` includes this for local stacks).

## Hot reload vs restart

| Mode | `PATCH /v1/workspace/settings` | Apply to running API |
|------|-------------------------------|----------------------|
| **Dev** (`SEAL_DEV_MODE=true`) | Persist to DB + apply `hot_reload: true` keys immediately | Optional; same as PATCH for hot keys |
| **Prod** (`SEAL_DEV_MODE=false`) | Persist to DB only; hot keys in `pending_apply` | `POST /v1/workspace/settings/apply` (dashboard **Apply to API**) |

| Key type | Notes |
|----------|--------|
| `hot_reload: true` | e.g. guardrails, char limits, `llm_model`, `rag_top_k` |
| `hot_reload: false` | e.g. `vector_store`, `cors_origins` — restart API container |

Field metadata: `packages/core/seal_core/workspace/settings_schema.py`.

## Dashboard

Operational dashboard (`apps/web`, port **3001**): **Query**, **Chat**, **Catalog**, **Settings**, **Vector**. Docs: `/docs/dashboard`.

## Startup

On lifespan startup: load workspace overrides (Postgres → file → env) into the settings singleton; apply catalog description overrides from workspace storage onto the registry after YAML load.

## Guardrails in workspace schema

Hot-reloadable from the dashboard: `guardrails_enabled`, `guardrails_fail_closed`, `max_query_chars`, `max_chat_message_chars`, `max_chat_history_chars`. See [guardrails.md](guardrails.md).
