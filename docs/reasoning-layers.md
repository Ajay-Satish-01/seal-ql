# Layered reasoning (chat + query)

**Doc index:** [README.md](README.md) · **Metadata contract:** [chat-metadata.md](chat-metadata.md) · **Chat flow:** [how-seal-works.md](how-seal-works.md)

Seal adds optional **layered reasoning** on `/v1/chat` and `/v1/query`: clarifying questions when requirements are thin, analytical follow-ups, data-backed research notes, and (chat only) inferred context from prior session turns.

Responses expose reasoning in **both** assistant-visible text and structured `metadata.reasoning` (flat on SSE `seal.meta`).

## Layer types

| Layer | Chat | Query | When |
| ----- | ---- | ----- | ---- |
| `inferred_context` | yes | no | Pre-execution; prior assistant turns |
| `clarification` | yes | yes | Pre-execution; ambiguous or underspecified input |
| `analysis_followups` | LLM answer | yes | Chat: `ChatAnswer` / stream enrichment; query: post layer |
| `research_notes` | LLM answer | yes | Chat: `ChatAnswer` / stream enrichment; query: post layer + planner |

When `clarification_required` is true and `clarifying_questions` is non-empty, routes return clarifying prompts **before** running SQL (chat early branch; query returns `message` with empty `sql`).

Clarification policy (chat decision LLM + heuristics):

- Infer tables, columns, and metrics from schema/catalog — never ask the user which table or schema area to use.
- Prefer executing with reasonable defaults (e.g. all available history, primary numeric measure) over blocking on thin ambiguity.
- Ask clarifying questions only for genuine, user-specific business choices that cannot be inferred from schema or prior turns.

## Architecture

```text
ReasoningOrchestrator (packages/core/seal_core/reasoning/)
    ├─ pre_execution: InferredContextLayer (chat), ClarificationLayer
    └─ post_execution: AnalysisFollowupsLayer, ResearchNotesLayer
```

- **Chat** runs **pre-execution** layers in `ChatService`, merges heuristic output with `ChatDecision`, then produces follow-ups and research notes via the **answer LLM** (`ChatAnswer` / stream enrichment) — not via post-execution heuristic layers.
- **Query** calls pre- and **post-execution** layers in `QueryService` (`seal_core/pipeline/query_service.py`; stateless; no session history).
- Layers are **fail-open**: failures set `layers_unavailable` and other layers still run.

## Configuration

Env vars (also workspace-hot-reloadable where noted in `settings_schema.py`):

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `REASONING_ENABLED` | `true` | Global toggle for heuristic layers |
| `REASONING_CHAT_ENABLED` | `true` | Heuristic pre-layers on `/v1/chat` |
| `REASONING_QUERY_ENABLED` | `true` | Heuristic pre/post layers on `/v1/query` |
| `REASONING_CLARIFICATION_ENABLED` | `true` | Heuristic clarification layer |
| `REASONING_ANALYSIS_FOLLOWUPS_ENABLED` | `true` | Query post-layer follow-ups (not chat) |
| `REASONING_RESEARCH_NOTES_ENABLED` | `true` | Query post-layer research notes (not chat) |
| `REASONING_LATENCY_BUDGET_MS` | `500` | Per-phase heuristic budget (`0` = unlimited) |

`REASONING_*` toggles control **heuristic layers** only. The orchestrator still runs; disabled layers return empty partial metadata. On chat, `ChatDecision` and the answer LLM can still set `inferred_context`, `clarifying_questions`, `analysis_followups`, and `research_notes` in `metadata.reasoning` regardless of these flags. `REASONING_ANALYSIS_FOLLOWUPS_ENABLED` and `REASONING_RESEARCH_NOTES_ENABLED` affect query post layers only.

## Adding a custom reasoning layer

1. Implement `ReasoningLayer` in `seal_core/reasoning/protocol.py` (`name`, `phase`, `enabled`, `run`).
2. Register on the orchestrator:
   - **Fork for production:** extend `build_default_orchestrator()` in `seal_core/reasoning/orchestrator.py`, or call `orchestrator.register(MyLayer())` on the instance passed to `ChatService` / query handling in `apps/api/app/main.py` lifespan.
   - There is no `SEAL_REASONING_LAYERS` env var yet (unlike `SEAL_ENHANCERS` for prompt enhancers).
3. Return partial `ReasoningLayerResult` fields; the orchestrator merges and dedupes.
4. If new metadata keys are needed, extend `ReasoningMetadata` and run the [chat-metadata](chat-metadata.md) contract checklist (OpenAPI, `stream_meta_metadata_keys.json`, shared TS).

Programmatic helpers on `ReasoningOrchestrator` — `run_clarification_only` and `run_full` — are for integrators and tests; the default HTTP routes use `run_pre` / `run_post` only.

## Onboarding a new database engine

Reasoning layers must **not** hard-code `postgres` / `duckdb`. Use the capability adapter:

1. Register the backend in `DatabaseRegistry` ([multi-database.md](multi-database.md)).
2. Ensure `DatabaseBundle.dialect` is set correctly at registry build time.
3. Extend `DatabaseCapabilities.from_bundle()` in `seal_core/reasoning/models.py` when the new engine exposes distinct features (JSON columns, time-series functions, etc.).
4. Optional: add a **capability enricher** layer that reads `ctx.database_capabilities` and appends `research_notes` — no changes to chat/query routes required.

No reasoning-specific route changes are needed when adding a database id; only registry + capability metadata.

## Code

- `packages/core/seal_core/reasoning/` — models, layers, orchestrator, config
- `packages/core/seal_core/chat/service.py` — chat integration
- `packages/core/seal_core/pipeline/query_service.py` — query integration (`apps/api/app/routes/query.py` delegates)
