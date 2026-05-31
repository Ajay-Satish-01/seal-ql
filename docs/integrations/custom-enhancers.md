# Custom prompt enhancers

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

`EnhancementContext.stage` is `decision` or `answer` when called from `ChatService`. Use it to inject different context per phase.

## Failure behavior

Exceptions in an enhancer are logged; the orchestrator continues with the previous prompt (**fail open**).

## What to expect

- Applied enhancer names appear in `metadata.enhancement.applied` on chat JSON and in SSE `seal.meta` events.
- Disabling enhancement on a request (`enhancement: false`) skips the entire chain, including custom enhancers.

See [../chat-enhancement.md](../chat-enhancement.md) and `/docs/prompt-enhancement`.
