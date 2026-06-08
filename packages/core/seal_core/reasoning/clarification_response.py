"""Shared clarification short-circuit helpers for chat and query routes."""

from __future__ import annotations

from typing import Any

from seal_core.reasoning.models import (
    ReasoningMetadata,
    format_reasoning_message,
    normalize_reasoning_clarification,
)


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
