# How Seal works

Contributor-oriented overview of request flow, LLM usage, and safety boundaries. User-facing copy lives on the docs site at `/docs/how-it-works`.

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
| `POST /v1/query` | HTTP 400 `query_out_of_scope` |
| `POST /v1/chat` | HTTP 200 refusal (`REFUSAL_SYSTEM` + `ChatAnswer`), no SQL/RAG |

See [guardrails.md](guardrails.md).

## Query path

`apps/api/app/routes/query.py`:

1. Resolve `database_id` → `DatabaseRegistry.get()` (**404** if unknown)
2. `classify_scope`
3. `bundle.introspector.introspect()` — catalog/semantic only when `database_id=default`
4. `execute_natural_language_query()` — planner → validate → sanitize → execute → repair loop
5. `ChartEngine.generate()` — response `metadata.database_id`

No chat enhancement chain on this path.

See [multi-database.md](multi-database.md) for registry config, DuckDB URL normalization, and limitations.

## Chat path

`seal_core/chat/service.py` (`ChatService`):

1. API resolves `database_id` → registry (**404** if unknown)
2. `SessionStore` — reject `database_id` change after pin (`SessionDatabaseMismatchError` → HTTP 400)
3. `_scope_gate` → metadata `scope`
4. `_chat_decision` → `ChatDecision.needs_data` (enhancement at `stage=decision` when enabled)
5. If `needs_data`: `ContextRetriever.select_tables` + `execute_natural_language_query` using bundle executor (+ optional chart)
6. `_answer_system` (enhancement at `stage=answer`) + answer LLM or SSE stream

Streaming: `seal.meta` (includes `database_id`) then token deltas; mismatch errors before SSE starts.

**Session pinning:** `_complete_turn` sets `state.database_id` only after a successful in-scope JSON or completed stream turn. Refusals do not pin. Follow-ups must repeat the same `database_id`.

Non-default `database_id`: catalog/semantic omitted from planner; `VectorRagEnhancer` skipped (index built from default only).

## Shared SQL pipeline

`seal_core/pipeline/execute.py` — used by query route and chat data path:

- `planner.generate_plan` (structured `QueryPlan`)
- `SQLValidator` / `SQLSanitizer`
- `executor.execute`
- Repair: replan on validation/execution errors (default `max_attempts=3`)

## Enhancement chain

Default order (`EnhancementOrchestrator`):

1. `SchemaAwareEnhancer`
2. `VectorRagEnhancer` (skipped if `in_scope=false`, `VECTOR_STORE=none`, or non-default `database_id`)
3. `MultiTurnEnhancer`

Append: `SEAL_ENHANCERS=dotted.path.Class`

See [chat-enhancement.md](chat-enhancement.md).

## Configuration layers

1. `.env` / `Settings`
2. `config/workspace.json` (read fallback)
3. `seal_app.workspace_kv` (Postgres, primary writes)

See [workspace-api.md](workspace-api.md). Full env tables: docs site `/docs/configuration`.

## Related docs

| Doc | Topic |
|-----|--------|
| [multi-database.md](multi-database.md) | `database_id` routing and registry |
| [guardrails.md](guardrails.md) | Scope gate env and behavior |
| [chat-enhancement.md](chat-enhancement.md) | Enhancer hooks and env |
| [workspace-api.md](workspace-api.md) | Workspace HTTP API |
| [integrations/](integrations/) | Agents, vector stores, custom enhancers |
