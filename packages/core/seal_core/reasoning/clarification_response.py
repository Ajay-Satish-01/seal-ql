"""Shared clarification short-circuit helpers for chat and query routes."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from seal_core.reasoning._constants import (
    LARGE_SCHEMA_THRESHOLD,
    has_specific_intent,
    has_table_hint,
)
from seal_core.reasoning.merge import merge_reasoning_metadata
from seal_core.reasoning.models import (
    ReasoningContext,
    ReasoningMetadata,
    format_reasoning_message,
    normalize_reasoning_clarification,
)

if TYPE_CHECKING:
    from seal_core.reasoning.orchestrator import ReasoningOrchestrator


def clarification_message(
    reasoning: ReasoningMetadata,
    *,
    include_inferred: bool = True,
) -> str:
    """User-visible assistant text for clarification-only responses."""
    return format_reasoning_message(
        normalize_reasoning_clarification(reasoning),
        include_inferred=include_inferred,
    )


def clarification_metadata_reasoning(reasoning: ReasoningMetadata) -> dict[str, Any]:
    """Serialized reasoning block for clarification metadata."""
    return normalize_reasoning_clarification(reasoning).model_dump(exclude_none=True)


def should_probe_schema_for_clarification(
    user_message: str,
) -> bool:
    """Whether schema-size probing is likely to add clarification signal."""
    text = user_message.strip().lower()
    if not text:
        return False
    return not has_specific_intent(text) and not has_table_hint(text)


async def merge_large_schema_clarification(
    orchestrator: ReasoningOrchestrator,
    pre_reasoning: ReasoningMetadata,
    ctx: ReasoningContext,
    *,
    schema_table_count: int,
    threshold: int = LARGE_SCHEMA_THRESHOLD,
) -> ReasoningMetadata:
    """Re-run clarification when schema size was unknown on the first pass."""
    if schema_table_count <= threshold:
        return pre_reasoning
    schema_ctx = replace(ctx, schema_table_count=schema_table_count)
    schema_clarify = await orchestrator.run_clarification_only(schema_ctx)
    return normalize_reasoning_clarification(
        merge_reasoning_metadata(pre_reasoning, schema_clarify)
    )
