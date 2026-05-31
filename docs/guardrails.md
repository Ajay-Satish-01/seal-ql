# LLM guardrails (scope gate)

Seal classifies every natural-language request on `POST /v1/query` and `POST /v1/chat` **before** planners, SQL execution, vector RAG, or multi-step chat models run.

**User-facing guide:** docs site `/docs/guardrails`  
**Pipeline context:** [how-seal-works.md](how-seal-works.md)

## Purpose

The API is scoped to **data analytics** — SQL, schema, catalog, metrics, charts — not general assistant use. The scope gate limits cost, abuse, and hallucinated SQL on off-topic prompts.

## Classification pipeline

`classify_scope(text, channel="query"|"chat")` in `packages/core/seal_core/guardrails/scope.py`:

| Stage | What happens | `metadata.scope.source` (chat) |
|-------|----------------|----------------------------------|
| Disabled | `GUARDRAILS_ENABLED=false` → allow all | `disabled` |
| Limits | Over `MAX_QUERY_CHARS` / `MAX_CHAT_MESSAGE_CHARS` | `limits` |
| Heuristics | Keywords → in-scope; regex → out-of-scope; else defer | `heuristic` |
| LLM | Instructor `ScopeDecision` via LiteLLM | `llm` |
| Classifier error | `GUARDRAILS_FAIL_CLOSED=true` → out-of-scope | `llm` |

Heuristic patterns live in `guardrails/heuristics.py` (data keywords, injection/off-topic regex).

## After classification

| Path | In scope | Out of scope |
|------|----------|--------------|
| `POST /v1/query` | Introspect → `execute_natural_language_query` → chart | HTTP **400** `query_out_of_scope` |
| `POST /v1/chat` | Decision → optional SQL → answer / stream | HTTP **200** refusal (`REFUSAL_SYSTEM` only); `metadata.refusal=true` |

Out-of-scope chat **does not** run `ChatDecision`, SQL, or vector RAG (`EnhancementContext.in_scope=false`).

## In scope (examples)

- Analytics questions (counts, trends, filters, aggregates)
- Schema and catalog help (tables, columns, relationships)
- Business-metric language grounded in the data catalog

## Out of scope (examples)

- General knowledge, creative writing, unrelated coding
- Prompt-injection patterns (e.g. “ignore previous instructions”)
- Inputs over configured character limits

## Chat-specific rules

- `system` role in client `messages` overrides → HTTP 400
- `include_charts` does not bypass scope or decision — SQL runs only when `ChatDecision.needs_data` is true

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `GUARDRAILS_ENABLED` | `true` | Master switch |
| `GUARDRAILS_FAIL_CLOSED` | `true` | Classifier errors → out-of-scope |
| `MAX_QUERY_CHARS` | `4000` | `/v1/query` input cap |
| `MAX_CHAT_MESSAGE_CHARS` | `8000` | Single chat message cap |
| `MAX_CHAT_HISTORY_CHARS` | `32000` | Total `messages` override cap |

Hot-reload via workspace when `SEAL_DEV_MODE=true`; production uses `POST /v1/workspace/settings/apply` after PATCH. See [workspace-api.md](workspace-api.md).

Docs site **Configuration reference** (`/docs/configuration#guardrails`) includes “what to expect” per variable.

## Code

- `packages/core/seal_core/guardrails/` — models, heuristics, `classify_scope`, prompts
- `packages/core/seal_core/chat/service.py` — `_scope_gate`, `_refusal_turn`, `_refusal_stream`
- `apps/api/app/routes/query.py` — query gate before planner
