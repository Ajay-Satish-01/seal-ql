"""Chain PromptEnhancer implementations."""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING, Any

from seal_core.enhancement.multiturn import MultiTurnEnhancer
from seal_core.enhancement.schema_enhancer import SchemaAwareEnhancer
from seal_core.enhancement.vector_rag import VectorRagEnhancer
from seal_core.settings import get_settings

if TYPE_CHECKING:
    from seal_core.chat.models import ChatMessage
    from seal_core.enhancement.context import EnhancementContext
    from seal_core.enhancement.protocol import PromptEnhancer

logger = logging.getLogger(__name__)

_REQUIRED_ENHANCER_METHODS = ("enabled", "enhance_system_prompt", "enhance_user_messages")


def _validate_enhancer(enhancer: Any, source: str) -> PromptEnhancer:
    if not isinstance(getattr(enhancer, "name", None), str):
        raise TypeError(f"Enhancer {source} is missing a string 'name' attribute")
    missing = [m for m in _REQUIRED_ENHANCER_METHODS if not callable(getattr(enhancer, m, None))]
    if missing:
        raise TypeError(f"Enhancer {source} does not implement PromptEnhancer: missing {missing}")
    return enhancer


def _load_enhancer(dotted: str) -> PromptEnhancer:
    module_path, _, class_name = dotted.rpartition(".")
    if not module_path:
        raise ValueError(f"Invalid enhancer path (expected 'module.Class'): {dotted!r}")
    module = importlib.import_module(module_path)
    return _validate_enhancer(getattr(module, class_name)(), dotted)


class EnhancementOrchestrator:
    def __init__(self, enhancers: list[PromptEnhancer]) -> None:
        self._enhancers: list[PromptEnhancer] = [
            _validate_enhancer(e, type(e).__name__) for e in enhancers
        ]

    def vector_rag_available(self) -> bool:
        """Return False only when a VectorRagEnhancer uses a no-op store.

        When no vector enhancer is registered, returns True (vector RAG is not disabled,
        it is simply absent from the chain).
        """
        from seal_core.vector.noop_store import NoopVectorStore

        for enh in self._enhancers:
            if isinstance(enh, VectorRagEnhancer):
                return not isinstance(enh._store, NoopVectorStore)
        return True

    async def enhance_system_prompt(self, ctx: EnhancementContext) -> str:
        prompt = ctx.base_system_prompt
        applied: list[str] = list(ctx.metadata.get("applied", []))

        for enh in self._enhancers:
            if enh.name in applied:
                continue
            if not enh.enabled(ctx):
                continue
            child = ctx.model_copy(deep=True)
            child.base_system_prompt = prompt
            try:
                prompt = await enh.enhance_system_prompt(child)
                applied.append(enh.name)
            except Exception as e:
                logger.warning("Enhancer %s failed: %s", enh.name, e)

        ctx.metadata["applied"] = applied
        return prompt

    async def enhance_user_messages(self, ctx: EnhancementContext) -> list[ChatMessage]:
        messages = list(ctx.messages)
        for enh in self._enhancers:
            if not enh.enabled(ctx):
                continue
            child = ctx.model_copy(deep=True)
            child.messages = messages
            try:
                messages = await enh.enhance_user_messages(child)
            except Exception as e:
                logger.warning("Enhancer %s messages failed: %s", enh.name, e)
        return messages


def build_default_orchestrator(
    *,
    catalog: Any | None,
    semantic_registry: Any | None,
    vector_store: Any,
) -> EnhancementOrchestrator:
    enhancers: list[PromptEnhancer] = [
        SchemaAwareEnhancer(catalog=catalog, semantic_registry=semantic_registry),
        VectorRagEnhancer(vector_store),
        MultiTurnEnhancer(),
    ]
    settings = get_settings()
    if settings.seal_enhancers:
        for dotted in settings.seal_enhancers.split(","):
            dotted = dotted.strip()
            if dotted:
                enhancers.append(_load_enhancer(dotted))
    return EnhancementOrchestrator(enhancers)
