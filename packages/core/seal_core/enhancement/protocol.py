"""PromptEnhancer protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from seal_core.chat.models import ChatMessage
    from seal_core.enhancement.context import EnhancementContext


class PromptEnhancer(Protocol):
    name: str

    def enabled(self, ctx: EnhancementContext) -> bool: ...

    async def enhance_system_prompt(self, ctx: EnhancementContext) -> str: ...

    async def enhance_user_messages(self, ctx: EnhancementContext) -> list[ChatMessage]: ...
