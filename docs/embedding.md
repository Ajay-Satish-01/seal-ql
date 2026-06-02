# Embedding Seal (OSS capability layer)

**User-facing guide:** docs site [`/docs/embedding`](http://localhost:3000/docs/embedding).

Authoritative reference for teams embedding Seal behind their own product API, agent runtime, or internal tools. See also [README.md](README.md) (full `docs/` index), [../DEPLOYMENT.md](../DEPLOYMENT.md), [../CONTRIBUTORS.md](../CONTRIBUTORS.md). Covers `database_id` routing, unified execution metadata, guardrails with `suggested_queries`, and session pinning.

## Responsibility split

| Your application | Seal |
| ---------------- | ---- |
| End-user identity (SSO, sessions, RBAC) | Shared `X-API-Key` for machine-to-machine access to `/v1/*` |
| Which tenant or workspace may run analytics | `database_id` routing to **pre-registered** backends only |
| Rate limits, billing, audit logs for your product | Scope guardrails, SQL AST validation, read-only execution |
| UI for charts, chat threads, saved questions | NL → SQL pipeline, Vega-Lite specs, optional chat sessions |
| Holding LLM provider keys in your VPC (optional) | LiteLLM + Instructor inside the API container |

Seal is a **capability layer**, not a full analytics product. Treat it like an internal microservice: your backend holds `SEAL_API_KEY`, calls Seal over HTTPS, and returns results to clients.

See [integrations/agent-frameworks.md](integrations/agent-frameworks.md) for HTTP tool manifests (`config/seal-tools.openai.json`).

## Deployment patterns

| Pattern | When to use | Config |
| ------- | ----------- | ------ |
| **One Seal, one DB** | Single analytics Postgres or DuckDB | `DATABASE_URL` only; omit `databases.yaml` |
| **One Seal, multiple DBs** | Same process, several registered backends | `config/databases.yaml` or `SEAL_DATABASES` + `database_id` per request |
| **One Seal per database** | Hard tenant isolation, different credentials per DB | Separate compose stack / K8s deployment per tenant |
| **BFF / API gateway** | Browser or mobile clients | Your API validates JWT → calls Seal with `X-API-Key`; never expose Seal key to clients |

```text
  [Browser] ──JWT──► [Your API / BFF] ──X-API-Key──► [Seal API] ──SQL──► [Postgres / DuckDB]
```

Multi-database details: [multi-database.md](multi-database.md). Authentication: docs site `/docs/authentication`.

## Three boundaries

Embedders should reason about three independent safety and cost layers:

### 1. Scope (guardrails)

**Question:** Should this message trigger SQL, RAG, and planner LLM calls?

- Runs first on `POST /v1/query` and `POST /v1/chat`
- Out-of-scope **query** → HTTP **400** — FastAPI nests fields under `detail` (see [guardrails.md](guardrails.md) for the full JSON)
- Out-of-scope **chat** → HTTP **200** with `metadata.refusal` and `metadata.suggested_queries` (same list on SSE `seal.meta`)

```json
{
  "detail": {
    "detail": "query_out_of_scope",
    "reason": "off-topic pattern",
    "suggested_queries": ["Show order count by month", "What tables are available?"]
  }
}
```

SDKs expose this as `QueryOutOfScopeError` (`.reason`, `.suggested_queries`). See [guardrails.md](guardrails.md) and `/docs/guardrails`.

### 2. SQL (zero-trust)

**Question:** Is this generated statement safe to run?

- SQLGlot AST parse, schema validation, sanitizer, enforced `LIMIT`
- Blocks `DROP`, `DELETE`, `TRUNCATE`, DML/DDL, and dynamic limits
- Same pipeline for `/v1/query` and chat turns that execute SQL

See [zero-trust-sql.md](zero-trust-sql.md) and `/docs/zero-trust-sql`.

### 3. Enhancement and vector RAG

**Question:** What extra context is injected before the planner?

- Chat-only default chain: schema focus → optional vector RAG → multi-turn summaries
- Query path has **no** enhancement chain (guardrails → introspect → planner only)
- `VECTOR_STORE=none` skips embeddings entirely; chat still works

See [chat-enhancement.md](chat-enhancement.md), [integrations/vector-stores.md](integrations/vector-stores.md), and `/docs/vector-rag`.

```text
  Request
    → [1] classify_scope
    → (chat) enhancement chain incl. optional vector RAG
    → planner + [2] SQLGlot validate → execute
    → answer / chart
```

## `database_id`, security, and shared resources

### Security model

- Clients send **ids only** (`"default"`, `"analytics"`) — never connection URLs in JSON bodies
- URLs live in server config (`DATABASE_URL`, `SEAL_DATABASES_PATH`, `SEAL_DATABASES`)
- Unknown id → HTTP **404** `unknown_database_id`
- Protect Seal with `SEAL_API_KEY`; use `SEAL_AUTH_REQUIRED=true` in production

### Routing

| Endpoint | `database_id` |
| -------- | ------------- |
| `POST /v1/query` | JSON body |
| `POST /v1/chat` | JSON body on **every** turn |
| `GET /v1/schema` | Query param `?database_id=` |
| `GET /v1/catalog` | Global (default DB introspection only) |

Responses echo `metadata.database_id` (query/chat JSON) or top-level `database_id` on SSE `seal.meta`. See [chat-metadata.md](chat-metadata.md).

### Shared resources (current limitations)

| Resource | Behavior |
| -------- | -------- |
| Data catalog | Built from **default** introspection; not per-`database_id` |
| Semantic layer | Applied to planner only when `database_id=default` |
| Vector RAG index | Built from **default** schema; skipped on non-default with `metadata.enhancement.vector_skipped_reason` |
| Chat sessions | After a successful in-scope turn, session **pins** `database_id`; follow-ups must match or HTTP **400** `session_database_id_mismatch`. Refusals do not pin. |

Full tables and curl examples: [multi-database.md](multi-database.md).

## Agent integration

- Ship `config/seal-tools.openai.json` (synced to docs site via `make sync-docs-assets`)
- Tools: `seal_get_schema`, `seal_get_catalog`, `seal_query`, `seal_chat` — `seal_get_catalog` is global; schema/query/chat accept optional `database_id`
- Parse query guardrails failures as structured JSON (`QueryOutOfScopeError` in SDKs)

Guide: [integrations/agent-frameworks.md](integrations/agent-frameworks.md) · docs site `/docs/agent-frameworks`.

## Operational checklist for embedders

1. Run Seal behind your network; set `SEAL_API_KEY` and `SEAL_DISABLE_DOCS=true` in production.
2. Mount `config/` for catalog YAML if using descriptions (`DATA_CATALOG_PATH`).
3. Configure `LLM_MODEL` and provider keys (LiteLLM).
4. Call from your server SDK or HTTP; pass `database_id` when you register multiple backends.
5. Handle `metadata` / `seal.meta` execution fields and `suggested_queries` on refusals.
6. Use `GET /v1/schema?database_id=…` to verify the backend your app selected.

Dashboard smoke test: `apps/web` on port **3001** (database dropdown, Query/Chat/Schema). Docs: `/docs/dashboard`.

## Future work (not Phase 0)

| Item | Status |
| ---- | ------ |
| Per-database catalog YAML | Planned — today catalog is global from `default` |
| Per-database vector indexes | Planned — today index is default-only |
| Per-database semantic registries | Planned |

Session pinning to `database_id` **is** shipped; see [multi-database.md](multi-database.md#chat-sessions-and-database_id).

## Related docs

| Doc | Topic |
| --- | ----- |
| [how-seal-works.md](how-seal-works.md) | Query vs chat pipeline |
| [multi-database.md](multi-database.md) | Registry config and session pinning |
| [guardrails.md](guardrails.md) | Scope gate and refusal shapes |
| [chat-metadata.md](chat-metadata.md) | Execution metadata contract |
| [integrations/](integrations/) | Agents, vector stores, custom enhancers |
