# Chat prompt enhancement

Seal chains built-in `PromptEnhancer` implementations on every `POST /v1/chat` turn when `CHAT_ENHANCEMENT_ENABLED=true` (default).

## Default chain

1. **SchemaAwareEnhancer** — focused schema, FK hints, global data catalog
2. **VectorRagEnhancer** — top-K chunks when `VECTOR_STORE` is not `none`
3. **MultiTurnEnhancer** — rolling summary and message trimming

Append custom enhancers with `SEAL_ENHANCERS=dotted.path.to.YourEnhancer`.

## Environment

All chat tuning variables live in `.env.example` under **Chat / prompt enhancement**:

| Variable | Purpose | Default |
|----------|---------|---------|
| `CHAT_ENHANCEMENT_ENABLED` | Run the enhancer chain on `/v1/chat` | `true` |
| `CHAT_SESSION_TTL_SECONDS` | Session TTL (seconds) | `3600` |
| `CHAT_MAX_HISTORY_MESSAGES` | Max messages per session | `20` |
| `CHAT_SUMMARIZE_AFTER_MESSAGES` | Trigger summarization above this count | `12` |
| `CHAT_RECENT_MESSAGES` | Verbatim messages at answer stage | `6` |
| `CHAT_ANSWER_PREVIEW_ROWS` | SQL result rows fed to the answer LLM | `20` |
| `CHAT_MAX_CONTEXT_TABLES` | Max tables in schema/catalog context | `8` |

Docker Compose loads these from `.env` via `env_file`; you do not need to duplicate them in the `environment:` block unless overriding defaults.

## Hooks

- `enhance_system_prompt` runs **once per user message** before the first LLM call.
- `enhance_user_messages` runs before each stage (`decision`, `planner`, `answer`).

Enhancers fail open: errors log a warning and return the original prompt.

See the docs site **Prompt enhancement** page (`/docs/prompt-enhancement` on `apps/web`) for the user-facing guide.
