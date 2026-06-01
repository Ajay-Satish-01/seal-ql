# Chat and query execution metadata

Seal exposes a shared execution contract on `POST /v1/query` and on chat turns that run SQL. The same shapes are documented on the docs site at `/docs/execution-metadata`, surfaced in the operational dashboard (`apps/web` on port **3001**), and typed in SDKs and `shared/metadata-contract.ts`.

## Query (`POST /v1/query`)

Top-level `sql`, `columns`, `results`, `chart`, and nested `metadata`:

| Field | Description |
|-------|-------------|
| `database_id` | Routed database (default: `default`) |
| `row_count` | Rows returned |
| `execution_time_ms` | Wall time for execution |
| `truncated` | Result capped by policy |
| `warnings` | SQL boundary warnings |
| `repair_attempts` | Planner repair iterations used |
| `used_sql` | Always `true` on success |

## Chat JSON (`POST /v1/chat`, `stream=false`)

Same execution fields live under **`metadata`**, plus chat-specific keys:

| Field | Description |
|-------|-------------|
| `metadata.enhancement.enabled` | Whether the enhancement chain ran this turn |
| `metadata.enhancement.applied` | Enhancer names applied (e.g. `schema_aware`, `vector_rag`) |
| `metadata.enhancement.vector_skipped_reason` | `non_default_database` or `vector_store_disabled` when RAG cannot run |
| `metadata.enhancement.unavailable_reason` | `orchestrator_unavailable` when the client requested enhancement (e.g. `enhancement: true`) but no orchestrator is configured — including guardrails refusals; omitted when an orchestrator exists but the turn is a refusal |
| `metadata.scope` | Guardrails scope decision (`ScopeMetadata` in OpenAPI) |
| `metadata.refusal` | `true` on guardrails refusal |
| `metadata.suggested_queries` | Up to 3 example in-scope data questions on refusal (heuristic or refusal LLM) |
| `metadata.sql_error` | `true` when the data path failed (no `sql`, `used_sql=false`) |

`metadata.scope` fields:

| Field | Type / values |
|-------|----------------|
| `in_scope` | `boolean` |
| `reason` | Short classifier or heuristic reason (string) |
| `source` | `heuristic` \| `llm` \| `limits` \| `disabled` (see [guardrails.md](guardrails.md)) |

`metadata.enhancement` enum fields (when set):

| Field | Allowed values |
|-------|----------------|
| `vector_skipped_reason` | `non_default_database`, `vector_store_disabled` |
| `unavailable_reason` | `orchestrator_unavailable` |

`used_sql` is `true` only after **successful** SQL execution.

## Chat SSE (`stream=true`)

The first event is `event: seal.meta`. Its `data:` line is a **flat** JSON object (not wrapped in `metadata`):

- Stream fields: `session_id`, `sources`, `sql`, `results`, `columns`, `chart`, `scope`
- Same execution and `enhancement` fields as JSON chat, at the top level
- `refusal` / `sql_error` / `suggested_queries` when applicable

OpenAPI models this as `ChatStreamMeta`; wire format is SSE-framed (`event:` / `data:`), not a raw JSON body.

## Validation

- Demo query fixtures: `scripts/response_validation.py` → `validate_query_response`
- Chat JSON shape: `validate_chat_response`
- Query `metadata`: `validate_query_metadata` (successful queries require full execution keys and `used_sql: true`)
- `seal.meta` payload: `validate_stream_meta_event` (includes `scope.source` and enhancement reason enums when present)
- At runtime, `ChatService` and the query route call `enforce_*` helpers; invalid payloads are logged. Under strict mode, raises `InvalidQueryMetadataError`, `InvalidStreamMetaError`, or `InvalidChatMetadataError` (subclasses of `MetadataValidationError`). Set `STRICT_STREAM_META_VALIDATION=true` (alias `STRICT_METADATA_VALIDATION`, workspace hot-reload key `strict_stream_meta_validation`) to fail the HTTP request instead of only logging.

Flatten helpers (keep in sync): `chat_response_to_stream_meta` (Python) and `chatResponseToStreamMeta` (`shared/metadata-contract.ts`); metadata keys in `config/stream_meta_metadata_keys.json`. Golden cases in `tests/fixtures/chat_flatten_golden.json` (`pnpm run verify:chat-flatten`). Validation parity matrix in `tests/fixtures/stream_meta_validation_matrix.json` (`pnpm run verify:stream-meta` in `apps/docs` / `make check`).

**SDK / client wire types:** Pydantic models in `apps/api/app/schemas.py` → `make openapi` → TypeScript `openapi-typescript` (`make openapi-ts`) → committed `sdks/typescript/src/generated/openapi.ts`. `scripts/generate_openapi.py` registers models referenced only in manual route responses (for example `ChatStreamMeta`). CI: `make verify-openapi-sync`. Do not duplicate `QueryMetadata` / `ChatStreamMeta` field lists in the SDK by hand.

**Python SDK:** TypedDicts / Pydantic models in `sdks/python/seal/` (including SSE `meta` and `meta_error` events in `_sse.py`).

Client-side SSE checks: `shared/stream-meta.ts` (`parseStreamMeta` / `tryParseStreamMeta` / `partialStreamMetaFromRaw`), with `shared/chat-sse-events.ts` (`mapChatSseEvent`) shared by `apps/docs` and `apps/web`. Invalid meta yields `meta_error` while preserving `session_id` / `database_id` when present.

## Dashboard (`apps/web`)

| Page | Metadata source |
|------|-----------------|
| **Query** (`/query`) | `response.metadata` after each `POST /v1/query` |
| **Chat** (`/chat`) | Flat fields from the first SSE `seal.meta` event (badges + JSON panel) |

The dashboard validates `seal.meta` with `mapChatSseEvent` and shows an info toast if the payload is malformed, while still applying partial session fields and streaming answer tokens when possible.

See also [chat-enhancement.md](chat-enhancement.md), [multi-database.md](multi-database.md), and the docs site [Operational dashboard](http://localhost:3000/docs/dashboard) page.
