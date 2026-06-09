# Chat prompt enhancement

Seal chains built-in `PromptEnhancer` implementations on `POST /v1/chat` when `CHAT_ENHANCEMENT_ENABLED=true` (default) and the scope gate marks the turn **in scope**.

**User-facing guide:** `/docs/prompt-enhancement` on the docs site  
**Doc index:** [README.md](README.md) · **Full chat + LLM flow:** [how-seal-works.md](how-seal-works.md) · **RAG boundary for embedders:** [embedding.md](embedding.md)  
**Execution metadata (query + chat JSON/SSE):** [chat-metadata.md](chat-metadata.md) — includes `metadata.enhancement.*`, `metadata.reasoning.*`, flat SSE `seal.meta`, OpenAPI type generation, and CI contract checks.

**Layered reasoning (separate from enhancement):** [reasoning-layers.md](reasoning-layers.md) — clarifying questions, follow-ups, research notes, chat-only inferred context via `ReasoningOrchestrator`.

## Where enhancement fits in a chat turn

```text
classify_scope (guardrails)
    → ReasoningOrchestrator (pre) — clarification / inferred context
    → [if clarification_required] early return with clarifying questions
    → EnhancementOrchestrator @ stage=decision → ChatDecision LLM
    → [if needs_data] execute_natural_language_query (planner, no enhancer on planner today)
    → ReasoningOrchestrator (post) — follow-ups / research notes
    → EnhancementOrchestrator @ stage=answer → Answer LLM (or SSE stream)
```

`/v1/query` does **not** use this chain; it calls the planner with full introspected schema via `execute_natural_language_query`.

## Default chain

1. **SchemaAwareEnhancer** — focused schema, FK hints, global data catalog (+ workspace descriptions)
2. **VectorRagEnhancer** — top-K chunks when `VECTOR_STORE` is not `none` and `in_scope=true`
3. **MultiTurnEnhancer** — rolling summary + `CHAT_RECENT_MESSAGES` verbatim at answer stage

Append custom enhancers: `SEAL_ENHANCERS=dotted.path.to.YourEnhancer` (after defaults).

## Hooks

| Method | When |
|--------|------|
| `enhance_system_prompt` | Once per orchestrator call (decision and answer stages) |
| `enhance_user_messages` | Before each stage; can trim/summarize messages |

Enhancers **fail open**: errors log a warning; the base prompt is returned.

Vector RAG is skipped when `in_scope=false` on `EnhancementContext` (out-of-scope turns never reach enhancers on the refusal path).

## Environment

From `.env.example` (**Chat / prompt enhancement**):

| Variable | Purpose | Default |
|----------|---------|---------|
| `CHAT_ENHANCEMENT_ENABLED` | Run enhancer chain on `/v1/chat` | `true` |
| `CHAT_SESSION_TTL_SECONDS` | Session TTL (seconds) | `3600` |
| `CHAT_MAX_HISTORY_MESSAGES` | Max messages per session | `20` |
| `CHAT_SUMMARIZE_AFTER_MESSAGES` | Summarize above this count | `12` |
| `CHAT_RECENT_MESSAGES` | Verbatim messages at answer stage | `6` |
| `CHAT_ANSWER_PREVIEW_ROWS` | SQL rows in answer prompt | `20` |
| `CHAT_MAX_CONTEXT_TABLES` | Max tables in schema/catalog context | `8` |

Guardrails env vars: [guardrails.md](guardrails.md). Vector: [integrations/vector-stores.md](integrations/vector-stores.md).

Per-request disable: `{"enhancement": false}` on `POST /v1/chat` (SDK: `enhancement=False` / `enhancement: false`).

Docker Compose loads vars from `.env` via `env_file`.

## Code

- `packages/core/seal_core/enhancement/orchestrator.py` — chain execution
- `packages/core/seal_core/chat/service.py` — `_chat_decision`, `_answer_system`
- `packages/core/seal_core/enhancement/schema_enhancer.py`, `vector_rag.py`, `multiturn.py`

Custom enhancers: [integrations/custom-enhancers.md](integrations/custom-enhancers.md).
