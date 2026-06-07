"""Merge orchestrator and LLM reasoning outputs.

``merge_reasoning_results`` (the low-level layer-result combiner) is defined
in ``models.py`` and re-exported here so callers have a single import path
for all merge operations.
"""

from __future__ import annotations

from seal_core.reasoning.models import (
    ReasoningLayerResult,
    ReasoningMetadata,
    merge_reasoning_results,
)

__all__ = [
    "merge_answer_reasoning",
    "merge_reasoning_metadata",
    "merge_reasoning_results",
]


def merge_reasoning_metadata(
    *parts: ReasoningMetadata | ReasoningLayerResult | None,
) -> ReasoningMetadata:
    """Combine multiple reasoning payloads into one normalized object."""
    layer_results: list[ReasoningLayerResult] = []
    preserved_applied: list[str] = []
    preserved_unavailable: dict[str, str] = {}
    for part in parts:
        if part is None:
            continue
        if isinstance(part, ReasoningMetadata):
            preserved_applied.extend(part.layers_applied)
            preserved_unavailable.update(part.layers_unavailable)
            layer_results.append(
                ReasoningLayerResult(
                    inferred_context=list(part.inferred_context),
                    analysis_followups=list(part.analysis_followups),
                    research_notes=list(part.research_notes),
                    clarifying_questions=list(part.clarifying_questions),
                    clarification_required=part.clarification_required,
                    layer_name="",
                )
            )
        else:
            layer_results.append(part)
    merged = merge_reasoning_results(layer_results)
    applied = list(dict.fromkeys([*preserved_applied, *merged.layers_applied]))
    unavailable = {**preserved_unavailable, **merged.layers_unavailable}
    return merged.model_copy(
        update={
            "layers_applied": applied,
            "layers_unavailable": unavailable,
        }
    )


def merge_answer_reasoning(
    pipeline: ReasoningMetadata | None,
    answer: ReasoningMetadata,
) -> ReasoningMetadata:
    """Merge chat answer-LLM reasoning without duplicating post-layer follow-ups."""
    base = pipeline or ReasoningMetadata()
    trimmed = base.model_copy(
        update={
            "analysis_followups": [],
            "research_notes": [],
        }
    )
    return merge_reasoning_metadata(trimmed, answer)
