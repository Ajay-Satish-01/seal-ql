# Custom prompt enhancers

**Doc index:** [../README.md](../README.md)

Implement `PromptEnhancer` in `packages/core/seal_core/enhancement/` (or your own package on `PYTHONPATH`):

```python
class MyEnhancer:
    name = "my_enhancer"

    def enabled(self, ctx: EnhancementContext) -> bool:
        return ctx.in_scope  # respect guardrails

    async def enhance_system_prompt(self, ctx: EnhancementContext) -> str:
        return ctx.base_system_prompt + "\n# extra context"

    async def enhance_user_messages(self, ctx: EnhancementContext) -> list[ChatMessage]:
        return ctx.messages
```

Register with `SEAL_ENHANCERS=my_package.MyEnhancer` (appended **after** SchemaAware → VectorRag → MultiTurn).

## Protocol

Required attributes/methods (validated at startup): `name`, `enabled`, `enhance_system_prompt`, `enhance_user_messages`.

## Stages

`ChatService` invokes enhancement at **`decision`** (before `ChatDecision`) and **`answer`** (before the final answer LLM or stream). Use `EnhancementContext.stage` to inject different system-prompt context per phase.

`EnhancementContext` also allows a `planner` stage in the type definition for forward compatibility; the default API path does not call enhancers during SQL planning.

## Message hook

`enhance_user_messages` is required on custom enhancers and is chained by `EnhancementOrchestrator`. Today `ChatService` calls **`enhance_system_prompt` only** and trims history itself. Implement `enhance_system_prompt` for production custom enhancers; use `enhance_user_messages` when calling `EnhancementOrchestrator.enhance_user_messages` directly or once `ChatService` wires the message hook.

## Failure behavior

Exceptions in an enhancer are logged; the orchestrator continues with the previous prompt (**fail open**).

## What to expect

- Applied enhancer names appear in `metadata.enhancement.applied` on chat JSON and in SSE `seal.meta` events.
- Disabling enhancement on a request (`enhancement: false`) skips the entire chain, including custom enhancers.

See [../chat-enhancement.md](../chat-enhancement.md) and `/docs/prompt-enhancement`.
