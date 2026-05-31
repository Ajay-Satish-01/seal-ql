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

1. `classify_scope`
2. `introspector.introspect()`
3. `execute_natural_language_query()` — planner → validate → sanitize → execute → repair loop
4. `ChartEngine.generate()`

No chat enhancement chain on this path.

## Chat path

`seal_core/chat/service.py` (`ChatService`):

1. `SessionStore` — TTL, `CHAT_MAX_HISTORY_MESSAGES`, `MAX_CHAT_HISTORY_CHARS` on overrides
2. `_scope_gate` → metadata `scope`
3. `_chat_decision` → `ChatDecision.needs_data` (enhancement at `stage=decision` when enabled)
4. If `needs_data`: `ContextRetriever.select_tables` + `execute_natural_language_query` (+ optional chart)
5. `_answer_system` (enhancement at `stage=answer`) + answer LLM or SSE stream

Streaming: `seal.meta` event then token deltas; partial assistant text persisted on stream end/error.

## Shared SQL pipeline

`seal_core/pipeline/execute.py` — used by query route and chat data path:

- `planner.generate_plan` (structured `QueryPlan`)
- `SQLValidator` / `SQLSanitizer`
- `executor.execute`
- Repair: replan on validation/execution errors (default `max_attempts=3`)

## Enhancement chain

Default order (`EnhancementOrchestrator`):

1. `SchemaAwareEnhancer`
2. `VectorRagEnhancer` (skipped if `in_scope=false` or `VECTOR_STORE=none`)
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
| [guardrails.md](guardrails.md) | Scope gate env and behavior |
| [chat-enhancement.md](chat-enhancement.md) | Enhancer hooks and env |
| [workspace-api.md](workspace-api.md) | Workspace HTTP API |
| [integrations/](integrations/) | Agents, vector stores, custom enhancers |
