"""Multi-turn conversation summarization and message trimming."""

from __future__ import annotations

from typing import TYPE_CHECKING

from seal_core.settings import get_settings

if TYPE_CHECKING:
    from seal_core.chat.models import ChatMessage
    from seal_core.enhancement.context import EnhancementContext


class MultiTurnEnhancer:
    name = "multi_turn"

    def enabled(self, ctx: EnhancementContext) -> bool:
        return len(ctx.messages) > 0

    async def enhance_system_prompt(self, ctx: EnhancementContext) -> str:
        summary = ctx.metadata.get("conversation_summary")
        if summary:
            return ctx.base_system_prompt + f"\n\n## Conversation summary\n{summary}\n"
        return ctx.base_system_prompt

    async def enhance_user_messages(self, ctx: EnhancementContext) -> list[ChatMessage]:
        if ctx.stage != "answer":
            return ctx.messages
        settings = get_settings()
        recent = settings.chat_recent_messages
        if len(ctx.messages) <= recent:
            return ctx.messages
        return ctx.messages[-recent:]
