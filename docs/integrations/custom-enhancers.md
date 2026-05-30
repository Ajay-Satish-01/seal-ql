# Custom prompt enhancers

Implement `PromptEnhancer` in `packages/core/seal_core/enhancement/`:

```python
class MyEnhancer:
    name = "my_enhancer"

    def enabled(self, ctx: EnhancementContext) -> bool:
        return True

    async def enhance_system_prompt(self, ctx: EnhancementContext) -> str:
        return ctx.base_system_prompt + "\n# extra context"

    async def enhance_user_messages(self, ctx: EnhancementContext) -> list[ChatMessage]:
        return ctx.messages
```

Register with `SEAL_ENHANCERS=my_package.MyEnhancer` (appended after the default chain).
