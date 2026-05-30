# Chat prompt enhancement

Seal chains built-in `PromptEnhancer` implementations on every `POST /v1/chat` turn when `CHAT_ENHANCEMENT_ENABLED=true` (default).

## Default chain

1. **SchemaAwareEnhancer** — focused schema, FK hints, global data catalog
2. **VectorRagEnhancer** — top-K chunks when `VECTOR_STORE` is not `none`
3. **MultiTurnEnhancer** — rolling summary and message trimming

Append custom enhancers with `SEAL_ENHANCERS=dotted.path.to.YourEnhancer`.

## Hooks

- `enhance_system_prompt` runs **once per user message** before the first LLM call.
- `enhance_user_messages` runs before each stage (`decision`, `planner`, `answer`).

Enhancers fail open: errors log a warning and return the original prompt.

See the docs site **Prompt enhancement** page (`/docs/prompt-enhancement` on `apps/web`) for the user-facing guide.
