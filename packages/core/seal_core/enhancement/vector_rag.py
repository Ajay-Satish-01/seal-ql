"""Vector RAG enhancement for system prompt."""

from __future__ import annotations

from typing import TYPE_CHECKING

from seal_core.settings import get_settings
from seal_core.vector.embeddings import embed_text
from seal_core.vector.noop_store import NoopVectorStore

if TYPE_CHECKING:
    from seal_core.chat.models import ChatMessage
    from seal_core.enhancement.context import EnhancementContext
    from seal_core.vector.protocol import VectorStore


class VectorRagEnhancer:
    name = "vector_rag"

    def __init__(self, store: VectorStore) -> None:
        self._store = store

    def enabled(self, ctx: EnhancementContext) -> bool:
        if not ctx.in_scope:
            return False
        if isinstance(self._store, NoopVectorStore):
            return False
        return not len(ctx.user_message.strip()) < 3

    async def enhance_system_prompt(self, ctx: EnhancementContext) -> str:
        settings = get_settings()
        try:
            embedding = await embed_text(ctx.user_message)
            hits = await self._store.search(embedding, top_k=settings.rag_top_k)
        except Exception:
            return ctx.base_system_prompt

        if not hits:
            return ctx.base_system_prompt

        lines = ["\n## Retrieved context\n"]
        budget = settings.rag_max_context_tokens * 4
        used = 0
        for doc in hits:
            chunk = doc.text.strip()
            if used + len(chunk) > budget:
                break
            lines.append(f"- {chunk}")
            used += len(chunk)
        return ctx.base_system_prompt + "\n".join(lines)

    async def enhance_user_messages(self, ctx: EnhancementContext) -> list[ChatMessage]:
        return ctx.messages
