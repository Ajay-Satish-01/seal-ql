# Multi-database routing (`database_id`)

**User-facing guide (start here):** docs site [`/docs/multi-database`](https://seal.dev/docs/multi-database) — step-by-step examples for integrators.

Contributor reference below. **Doc index:** [README.md](./README.md). For pipeline context see [how-seal-works.md](./how-seal-works.md). Embedder deployment patterns: [embedding.md](./embedding.md).

## Purpose

Seal routes each request to a **pre-configured** database identified by `database_id`. Clients pass an id string — never a connection URL. This supports:

- **Default analytics DB** — `DATABASE_URL` registers id `default`
- **Additional backends** — warehouse, DuckDB file, read replica, in-memory analytics, etc.

For strict tenant isolation, use **one Seal instance per tenant database** or map tenants to registered ids in your application layer (with your own auth in front of Seal).

## Quick reference — which endpoints use `database_id`?

| Endpoint | How to pass `database_id` | Default if omitted |
| -------- | ------------------------- | ------------------ |
| `POST /v1/query` | JSON body field `database_id` | `"default"` |
| `POST /v1/chat` | JSON body field `database_id` (every turn) | `"default"` |
| `GET /v1/schema` | Query parameter `?database_id=` | `"default"` |
| `GET /v1/catalog` | *(not per-database)* | Global catalog from **default** only |
| Agent tools `seal_query`, `seal_chat`, `seal_get_schema` | Tool argument `database_id` | `"default"` |

Responses echo the backend used:

- **Query:** `metadata.database_id`
- **Chat (JSON):** `metadata.database_id` (including refusals)
- **Chat (SSE):** top-level `database_id` on the flat `seal.meta` object (see [chat-metadata.md](chat-metadata.md))

## Reasoning capabilities for new databases

Layered reasoning (`metadata.reasoning`) is database-agnostic. When you add a backend:

1. Register it in `DatabaseRegistry` (this document).
2. Set `DatabaseBundle.dialect` correctly at build time.
3. Extend `DatabaseCapabilities.from_bundle()` in `seal_core/reasoning/models.py` only when the engine has distinct features (JSON columns, time-series helpers, etc.).
4. Optionally register a custom `ReasoningLayer` that reads `ctx.database_capabilities` — no changes to `/v1/chat` or `/v1/query` routes.

See [reasoning-layers.md](reasoning-layers.md).

## Configuration

| Source | Registers |
| ------ | --------- |
| `DATABASE_URL` | Always id `default` (required) |
| `SEAL_DATABASES_PATH` (default `config/databases.yaml`) | Additional ids when the file **exists**; missing file is ignored |
| `SEAL_DATABASES` (JSON env) | Additional ids; useful in Docker without mounting YAML |

Example YAML (`config/databases.example.yaml` → copy to `config/databases.yaml`):

```yaml
databases:
  analytics:
    url: duckdb:///data/analytics.duckdb
  warehouse:
    url: postgresql+asyncpg://reader@host:5432/warehouse
```

JSON env (non-default ids only):

```bash
SEAL_DATABASES='{"analytics":"duckdb:///data/analytics.duckdb","sandbox":":memory:"}'
```

### Rules at startup

- Duplicate ids in YAML/JSON → **startup error**
- Entry named `default` in YAML/JSON → **ignored**; `DATABASE_URL` always wins
- Unknown scheme in URL → **startup error** (`DatabaseConfigError`)
- Multiple non-default ids → warning log; catalog/vector remain on `default` only

### Connection URL formats

| Dialect | Accepted forms | Notes |
| ------- | -------------- | ----- |
| **Postgres** | `postgresql+asyncpg://user:pass@host:5432/db` | Standard Docker / `make up` default |
| **DuckDB file** | `duckdb:///absolute/or/relative/path.duckdb` | URL form; normalized to a file path internally |
| **DuckDB in-memory** | `:memory:` or `duckdb:///:memory:` | Ephemeral; new empty DB per API process |
| **DuckDB path** | `/data/analytics.duckdb` | Plain path (no scheme) also works |

DuckDB URLs like `duckdb:///data/file.duckdb` are **not** passed verbatim to the driver. `normalize_connection_url()` strips the scheme and uses the path (`/data/file.duckdb`). Remote DuckDB URLs (`duckdb://host/...`) are rejected.

Postgres URLs are passed through as configured (with `+asyncpg` stripped where needed for asyncpg).

Dialect is inferred from the URL **scheme**, not substrings in file paths (so `/tmp/postgres-exports.duckdb` is still DuckDB).

## Code path

Startup (`apps/api/app/main.py`):

1. `build_database_registry(settings)` → `app.state.database_registry`
2. Catalog sync, strict validation, and vector index build use the **`default`** bundle only

Per request:

| Route | Order of operations |
| ----- | ------------------- |
| `POST /v1/query` | Resolve `database_id` → **404 if unknown** → `classify_scope` → introspect → execute |
| `POST /v1/chat` | Resolve `database_id` → **404 if unknown** → `ChatService` (session check → scope → …) |
| `GET /v1/schema` | Resolve `database_id` → **404 if unknown** → introspect |

Unknown id → HTTP **404** with body detail `unknown_database_id`.

Empty `database_id` → HTTP **422** validation error.

Core modules:

- `packages/core/seal_core/database/config.py` — load URLs, `infer_dialect`, `normalize_connection_url`
- `packages/core/seal_core/database/registry.py` — `DatabaseBundle`, `DatabaseRegistry`
- `apps/api/app/database_routing.py` — `get_database_bundle()`, session mismatch detail helper

`ChatService` uses `bundle.executor` and `bundle.introspector` per turn from the request’s `database_id`.

## Chat sessions and `database_id`

Chat keeps conversation history in a pluggable session store (`CHAT_SESSION_STORE`):

- **`memory`** (default) — in-process only; TTL from `CHAT_SESSION_TTL_SECONDS`; list/resume via `GET /v1/chat/sessions` within the same API process.
- **`postgres`** — persistent rows in `seal_app.chat_sessions` / `chat_messages` (same app DB as workspace); survives restarts, Lambda, and multi-task ECS.

### Pinning rules

1. **First turn** on a new `session_id` — any registered `database_id` is allowed.
2. **After a successful in-scope turn** — the session **pins** that `database_id`.
3. **Follow-up turns** must send the **same** `database_id`, or the API returns HTTP **400** with structured detail:

```json
{
  "detail": {
    "code": "session_database_id_mismatch",
    "message": "Session '…' is pinned to database_id 'default'; got 'analytics'",
    "session_id": "…",
    "pinned_database_id": "default",
    "requested_database_id": "analytics"
  }
}
```

4. **Out-of-scope refusals** (guardrails) do **not** pin the session — you can retry the same `session_id` with a different `database_id` until one successful in-scope turn pins it.
5. **Streaming** (`stream: true`) — mismatch is returned as HTTP **400** before the SSE body starts (same as JSON chat).

Always pass `database_id` on **every** chat message in a session, not only the first.

## Shared resources (current limitations)

| Resource | Behavior |
| -------- | -------- |
| Data catalog (`DATA_CATALOG_PATH`) | Loaded once; auto-sync introspects **default** only |
| Semantic layer (`SEMANTIC_DIRECTORY`) | Single registry; applied to planner only for `database_id=default` |
| Vector RAG index | Built from **default** schema at startup |
| `SchemaAwareEnhancer` on non-default | Introspected schema only — no catalog/semantic prompt injection |
| `VectorRagEnhancer` on non-default | Skipped (index matches default) |

## API & SDK

### HTTP examples

```bash
# Query — analytics DuckDB
curl -s -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SEAL_API_KEY" \
  -d '{"query":"Count rows in daily_revenue","database_id":"analytics"}'

# Chat — follow-up (same database_id as first successful turn)
curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SEAL_API_KEY" \
  -d '{"message":"Break that down by week","session_id":"YOUR_SESSION_ID","database_id":"analytics"}'

# Schema
curl -s "http://localhost:8000/v1/schema?database_id=analytics" \
  -H "X-API-Key: $SEAL_API_KEY"
```

### Python SDK

```python
from seal import Seal

with Seal("http://localhost:8000", api_key="...") as client:
    result = client.query("Total orders", database_id="default")
    schema = client.schema(database_id="analytics")
    reply = client.chat("What tables exist?", database_id="analytics")
    for event in client.chat_stream("Summarize revenue", database_id="analytics"):
        ...
```

### TypeScript SDK

`query` takes the database id as the **second argument** (not an options object):

```typescript
const result = await client.query('Total orders', 'default');
const schema = await client.schema({ databaseId: 'analytics' });
const chat = await client.chat('What tables exist?', { databaseId: 'analytics' });
for await (const event of client.chatStream('Summarize', { databaseId: 'analytics' })) {
  ...
}
```

Agent tools: `config/seal-tools.openai.json` — each SQL-related tool accepts optional `database_id`.

## Deployment patterns

| Pattern | When |
| ------- | ---- |
| One Seal, one DB | Only `DATABASE_URL`; omit `databases.yaml` |
| One Seal, multiple DBs | `config/databases.yaml` or `SEAL_DATABASES` + pass `database_id` per request |
| DuckDB file in Docker | Mount host dir into container (e.g. `./data:/data`) and use `duckdb:///data/file.duckdb` |
| Multi-tenant SaaS | One Seal per tenant DB, or tenant → id mapping in your BFF |
| Read replica | Register id `replica` with read-only Postgres URL |

## Troubleshooting

| Symptom | Likely cause | What to do |
| ------- | ------------ | ---------- |
| `404 unknown_database_id` | Typo or config not loaded | Check YAML/JSON, restart API, read startup logs for `Registering database` |
| DuckDB IO / invalid database file | Bad path or empty file at path | Ensure directory exists in container; use `duckdb:///…` or plain path; file is created on first connect if missing |
| `400 session_database_id_mismatch` | Follow-up used different id than pinned session | Send same `database_id` or start a new `session_id` |
| SQL references wrong tables | Catalog/semantic from default applied to wrong mental model | Use `GET /v1/schema?database_id=…`; expect no catalog hints on non-default |
| Chat lacks RAG context on `analytics` | Vector index is default-only | Expected; enable separate instance or use `default` for RAG-heavy chat |

## Related docs

| Doc | Topic |
| --- | ----- |
| [embedding.md](./embedding.md) | Embedder guide — BFF pattern, three boundaries, operational checklist |
| Docs site `/docs/embedding` | User-facing embedding and boundary model |
| Docs site `/docs/multi-database` | Integrator guide with scenarios |
| Dashboard (`apps/web`, port 3001) | Database dropdown, Query/Chat/Schema with `database_id` |
| `GET /v1/databases` | List registered ids (dashboard + clients) |
| [how-seal-works.md](./how-seal-works.md) | Full query/chat pipeline |
| [integrations/agent-frameworks.md](./integrations/agent-frameworks.md) | HTTP tools |
| Docs site `/docs/configuration` | Env reference |
| Docs site `/docs/chat-qa` | Chat sessions and `database_id` |
| Docs site `/docs/chat-streaming` | SSE and `seal.meta` |
