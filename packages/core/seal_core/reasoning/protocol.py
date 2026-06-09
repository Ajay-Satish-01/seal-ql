"""ReasoningLayer protocol for pluggable reasoning extensions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from seal_core.reasoning.models import ReasoningContext, ReasoningLayerResult, ReasoningPhase


class ReasoningLayer(Protocol):
    """Contract for composable reasoning layers."""

    name: str
    phase: ReasoningPhase

    def enabled(self, ctx: ReasoningContext) -> bool: ...

    async def run(self, ctx: ReasoningContext) -> ReasoningLayerResult: ...
