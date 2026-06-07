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

## Architecture

```text
ReasoningOrchestrator (packages/core/seal_core/reasoning/)
    ├─ pre_execution: InferredContextLayer (chat), ClarificationLayer
    └─ post_execution: AnalysisFollowupsLayer, ResearchNotesLayer
```

- **Chat** wires the orchestrator in `ChatService` and merges LLM `ChatDecision` / `ChatAnswer` fields.
- **Query** calls the orchestrator in `apps/api/app/routes/query.py` (stateless; no session history).
- Layers are **fail-open**: failures set `layers_unavailable` and other layers still run.

## Configuration

Env vars (also workspace-hot-reloadable where noted in `settings_schema.py`):

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `REASONING_ENABLED` | `true` | Global toggle |
| `REASONING_CHAT_ENABLED` | `true` | `/v1/chat` reasoning |
| `REASONING_QUERY_ENABLED` | `true` | `/v1/query` reasoning |
| `REASONING_CLARIFICATION_ENABLED` | `true` | Clarifying-question branch |
| `REASONING_ANALYSIS_FOLLOWUPS_ENABLED` | `true` | Follow-up suggestions |
| `REASONING_RESEARCH_NOTES_ENABLED` | `true` | Research framing notes |
| `REASONING_LATENCY_BUDGET_MS` | `500` | Per-phase heuristic budget (`0` = unlimited) |

## Adding a custom reasoning layer

1. Implement `ReasoningLayer` in `seal_core/reasoning/protocol.py` (`name`, `phase`, `enabled`, `run`).
2. Register on the orchestrator: `orchestrator.register(MyLayer())` at app startup, or extend `build_default_orchestrator()`.
3. Return partial `ReasoningLayerResult` fields; the orchestrator merges and dedupes.
4. If new metadata keys are needed, extend `ReasoningMetadata` and run the [chat-metadata](chat-metadata.md) contract checklist (OpenAPI, `stream_meta_metadata_keys.json`, shared TS).

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
- `apps/api/app/routes/query.py` — query integration
