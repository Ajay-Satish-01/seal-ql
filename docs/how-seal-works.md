# How Seal works

Contributor-oriented overview of request flow, LLM usage, and safety boundaries. User-facing copy lives on the docs site at `/docs/how-it-works`. Doc index: [README.md](README.md).

## Stack

- **API** — `apps/api` (FastAPI), routes under `/v1/*`
- **Core** — `packages/core/seal_core/` (chat, planner, guardrails, enhancement, catalog, workspace, pipeline)
- **SQL** — `packages/sql/` (SQLGlot validator, sanitizer, executor)
- **Charts** — `packages/charts/` (Vega-Lite from plan + result, no LLM)
- **LLM** — LiteLLM + Instructor via `seal_core.llm.client`

## Guardrails

`classify_scope(text, channel="query"|"chat")` in `guardrails/scope.py`:

1. Return early if `GUARDRAILS_ENABLED=false`
2. Character limits (`MAX_QUERY_CHARS` / `MAX_CHAT_MESSAGE_CHARS`)
3. `heuristic_in_scope()` — keywords → in-scope; abuse/off-topic regex → out-of-scope; else `None`
4. Instructor `ScopeDecision` when heuristics defer
5. On classifier exception: out-of-scope if `GUARDRAILS_FAIL_CLOSED=true`

| Route | Out of scope |
|-------|----------------|
| `POST /v1/query` | HTTP 400 structured `detail` (`query_out_of_scope`, `reason`, `suggested_queries`) |
| `POST /v1/chat` | HTTP 200 refusal (`REFUSAL_SYSTEM` + `ChatAnswer`), no SQL/RAG |

See [guardrails.md](guardrails.md).

## Query path

`apps/api/app/routes/query.py`:

1. Resolve `database_id` → `DatabaseRegistry.get()` (**404** if unknown)
2. `bundle.introspector.introspect()` — schema for scope hints and execution
3. `classify_scope` (uses table-name hints from introspection)
4. `ReasoningOrchestrator.run_pre()` — optional clarification (`metadata.reasoning`, top-level `message`, no SQL)
5. `execute_natural_language_query()` — planner → validate → sanitize → execute → repair loop; catalog/semantic only when `database_id=default`
6. `ChartEngine.generate()` — Vega-Lite from plan + result
7. `ReasoningOrchestrator.run_post()` — follow-ups and research notes
8. Assemble response `metadata` (`database_id`, `used_sql: true`, execution stats; `enforce_query_metadata` on success)

No chat enhancement chain on this path. See [reasoning-layers.md](reasoning-layers.md).

See [multi-database.md](multi-database.md) for registry config, DuckDB URL normalization, and limitations.

## Chat path

`seal_core/chat/service.py` (`ChatService`):

1. API resolves `database_id` → registry (**404** if unknown)
2. `BaseSessionStore` — reject `database_id` change after pin (`SessionDatabaseMismatchError` → HTTP 400)
3. `_scope_gate` → metadata `scope`
4. `ReasoningOrchestrator.run_pre` — inferred context + clarification; early return when `clarification_required` (merged with `ChatDecision` clarification fields)
5. `_chat_decision` → `ChatDecision.needs_data` (`enhance_system_prompt` at `stage=decision` when enhancement enabled)
6. If `needs_data`: `ContextRetriever.select_tables` + `execute_natural_language_query` using bundle executor (+ optional chart)
7. `ReasoningOrchestrator.run_post` — on chat, post heuristic follow-up/research layers are skipped (`resolve_reasoning_config` is query-only for those layers)
8. `_answer_system` — `enhance_system_prompt` at `stage=answer`, then answer LLM or SSE stream; follow-ups and research notes come from `ChatAnswer` / stream enrichment (not query-style post layers)

Streaming: `seal.meta` (flat JSON with `database_id`, execution fields, `enhancement`, `scope` as `ScopeMetadata` with typed `source`, optional `refusal` / `sql_error`) then token deltas; mismatch errors before SSE starts. Server validates with `validate_stream_meta_event`; clients use `shared/stream-meta.ts` and `mapChatSseEvent` (`meta_error` on malformed payloads).

**Session pinning:** `_complete_turn` sets `state.database_id` only after a successful in-scope JSON or completed stream turn. Refusals do not pin. Follow-ups must repeat the same `database_id`.

Non-default `database_id`: catalog/semantic omitted from planner; `VectorRagEnhancer` skipped (index built from default only).

## Shared SQL pipeline

`seal_core/pipeline/execute.py` — used by query route and chat data path:

- `planner.generate_plan` (structured `QueryPlan`)
- `SQLValidator` / `SQLSanitizer` — see [zero-trust-sql.md](zero-trust-sql.md) and `/docs/zero-trust-sql`
- `executor.execute`
- Repair: replan on validation/execution errors (default `max_attempts=3`)

## Enhancement chain

Default order (`EnhancementOrchestrator`):

1. `SchemaAwareEnhancer`
2. `VectorRagEnhancer` (skipped if `in_scope=false`, `VECTOR_STORE=none`, or non-default `database_id`)
3. `MultiTurnEnhancer`

Append: `SEAL_ENHANCERS=dotted.path.Class`

See [chat-enhancement.md](chat-enhancement.md).

## Layered reasoning

`seal_core/reasoning/` — pluggable `ReasoningOrchestrator` shared by chat and query:

- Pre-execution: clarification, chat-only inferred context from session history
- Post-execution: analytical follow-ups, data-backed research notes
- Controlled by `REASONING_*` env vars (also workspace-hot-reloadable)

See [reasoning-layers.md](reasoning-layers.md).

## Configuration layers

1. `.env` / `Settings`
2. `config/workspace.json` (read fallback)
3. `seal_app.workspace_kv` (Postgres, primary writes)

See [workspace-api.md](workspace-api.md). Full env tables: docs site `/docs/configuration`.

## Related docs

| Doc | Topic |
|-----|--------|
| [embedding.md](embedding.md) | OSS embedder guide — responsibility split, deployment patterns, three boundaries |
| [multi-database.md](multi-database.md) | `database_id` routing and registry |
| [guardrails.md](guardrails.md) | Scope gate env and behavior |
| [chat-enhancement.md](chat-enhancement.md) | Enhancer hooks and env |
| [chat-metadata.md](chat-metadata.md) | Query/chat execution metadata (JSON vs SSE) |
| [reasoning-layers.md](reasoning-layers.md) | Layered reasoning orchestrator and DB onboarding |
| [workspace-api.md](workspace-api.md) | Workspace HTTP API |
| [integrations/](integrations/) | Agents, vector stores, custom enhancers |
