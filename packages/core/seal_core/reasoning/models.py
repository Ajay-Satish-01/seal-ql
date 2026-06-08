"""Structured models for layered reasoning outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from seal_core.chat.models import ChatMessage
    from seal_core.pipeline.execute import ExecuteQueryResult


class ReasoningPhase(StrEnum):
    """When a reasoning layer runs in the request lifecycle."""

    PRE_EXECUTION = "pre_execution"
    POST_EXECUTION = "post_execution"


class ReasoningMetadata(BaseModel):
    """User-facing reasoning summary surfaced in response metadata."""

    inferred_context: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Concise inferences from prior session state (chat only).",
    )
    analysis_followups: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Suggested analytical follow-up questions or angles.",
    )
    research_notes: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Data-backed observations or research framing notes.",
    )
    clarifying_questions: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Targeted questions to gather missing requirements.",
    )
    clarification_required: bool = Field(
        default=False,
        description="True when the request lacks sufficient context for a confident answer.",
    )
    layers_applied: list[str] = Field(
        default_factory=list,
        description="Reasoning layer names that contributed to this payload.",
    )
    layers_unavailable: dict[str, str] = Field(
        default_factory=dict,
        description="Layer name to short reason when a layer was skipped or failed.",
    )


@dataclass(frozen=True)
class DatabaseCapabilities:
    """Database-agnostic capability hints for reasoning layers."""

    database_id: str
    dialect: str
    supports_time_series: bool = True
    supports_json_columns: bool = False
    provider: str = "unknown"

    @classmethod
    def from_bundle(cls, *, database_id: str, dialect: str) -> DatabaseCapabilities:
        """Build capabilities from registry bundle metadata."""
        dialect_lower = dialect.lower()
        provider = "duckdb" if "duckdb" in dialect_lower else "postgres"
        if "postgres" in dialect_lower:
            provider = "postgres"
        return cls(
            database_id=database_id,
            dialect=dialect,
            supports_time_series=True,
            supports_json_columns=provider == "postgres",
            provider=provider,
        )


@dataclass(frozen=True)
class ReasoningContext:
    """Inputs shared by all reasoning layers.

    Immutable: use ``dataclasses.replace(ctx, field=value)`` to create
    a modified copy (e.g. with a different ``phase`` or ``schema_table_count``).
    """

    route: Literal["chat", "query"]
    user_message: str
    database_capabilities: DatabaseCapabilities
    phase: ReasoningPhase
    messages: tuple[ChatMessage, ...] | None = None
    exec_result: ExecuteQueryResult | None = None
    schema_table_count: int | None = None
    schema_table_names: tuple[str, ...] = ()
    prior_assistant_topics: tuple[str, ...] = ()


@dataclass
class ReasoningLayerResult:
    """Partial output from a single reasoning layer."""

    inferred_context: list[str] = field(default_factory=list)
    analysis_followups: list[str] = field(default_factory=list)
    research_notes: list[str] = field(default_factory=list)
    clarifying_questions: list[str] = field(default_factory=list)
    clarification_required: bool = False
    layer_name: str = ""
    unavailable_reason: str | None = None


def merge_reasoning_results(
    results: list[ReasoningLayerResult],
    *,
    max_items: int = 5,
) -> ReasoningMetadata:
    """Merge layer outputs into a single metadata payload."""
    inferred: list[str] = []
    followups: list[str] = []
    research: list[str] = []
    clarifying: list[str] = []
    clarification_required = False
    applied: list[str] = []
    unavailable: dict[str, str] = {}

    for result in results:
        if result.unavailable_reason:
            unavailable[result.layer_name] = result.unavailable_reason
            continue
        if result.layer_name:
            applied.append(result.layer_name)
        inferred.extend(result.inferred_context)
        followups.extend(result.analysis_followups)
        research.extend(result.research_notes)
        clarifying.extend(result.clarifying_questions)
        clarification_required = clarification_required or result.clarification_required

    def _dedupe(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            out.append(normalized)
            if len(out) >= max_items:
                break
        return out

    return ReasoningMetadata(
        inferred_context=_dedupe(inferred),
        analysis_followups=_dedupe(followups),
        research_notes=_dedupe(research),
        clarifying_questions=_dedupe(clarifying),
        clarification_required=clarification_required,
        layers_applied=applied,
        layers_unavailable=unavailable,
    )


REASONING_SECTION_HEADERS: tuple[str, ...] = (
    "**Context from our conversation**",
    "**A few details would help**",
    "**Clarifying questions**",
    "**Research notes**",
    "**Suggested follow-ups**",
)


def strip_reasoning_from_content(content: str) -> str:
    """Remove appended reasoning sections from persisted assistant text."""
    cut_at = len(content)
    for header in REASONING_SECTION_HEADERS:
        idx = content.find(header)
        if idx >= 0:
            cut_at = min(cut_at, idx)
    return content[:cut_at].strip()


def format_reasoning_message(
    reasoning: ReasoningMetadata,
    *,
    include_inferred: bool = True,
) -> str:
    """Build user-visible assistant text from structured reasoning layers."""
    sections: list[str] = []

    if include_inferred and reasoning.inferred_context:
        sections.append(
            f"{REASONING_SECTION_HEADERS[0]}\n"
            + "\n".join(f"- {item}" for item in reasoning.inferred_context)
        )

    if reasoning.clarification_required and reasoning.clarifying_questions:
        sections.append(
            f"{REASONING_SECTION_HEADERS[1]}\n"
            + "\n".join(f"- {q}" for q in reasoning.clarifying_questions)
        )
    elif reasoning.clarifying_questions:
        sections.append(
            f"{REASONING_SECTION_HEADERS[2]}\n"
            + "\n".join(f"- {q}" for q in reasoning.clarifying_questions)
        )

    if reasoning.research_notes:
        sections.append(
            f"{REASONING_SECTION_HEADERS[3]}\n"
            + "\n".join(f"- {n}" for n in reasoning.research_notes)
        )

    if reasoning.analysis_followups:
        sections.append(
            f"{REASONING_SECTION_HEADERS[4]}\n"
            + "\n".join(f"- {f}" for f in reasoning.analysis_followups)
        )

    return "\n\n".join(sections)


def append_reasoning_to_message(base_message: str, reasoning: ReasoningMetadata) -> str:
    """Append formatted reasoning sections to an existing assistant message."""
    extra = format_reasoning_message(reasoning, include_inferred=False)
    if not extra.strip():
        return base_message
    if not base_message.strip():
        return extra
    return f"{base_message.rstrip()}\n\n{extra}"


_DEFAULT_CLARIFYING_QUESTION = "What specific metric, entity, or time range should I use?"


def normalize_reasoning_clarification(reasoning: ReasoningMetadata) -> ReasoningMetadata:
    """Ensure clarification_required always ships actionable questions."""
    if reasoning.clarification_required and not reasoning.clarifying_questions:
        return reasoning.model_copy(update={"clarifying_questions": [_DEFAULT_CLARIFYING_QUESTION]})
    return reasoning


def should_return_clarification(reasoning: ReasoningMetadata) -> bool:
    """True when the response should short-circuit to clarification-only."""
    normalized = normalize_reasoning_clarification(reasoning)
    return normalized.clarification_required and bool(normalized.clarifying_questions)


def reasoning_suffix_delta(base_message: str, reasoning: ReasoningMetadata) -> str:
    """Return only the reasoning text not already present in base_message."""
    extra = format_reasoning_message(reasoning, include_inferred=False)
    if not extra.strip():
        return ""
    if extra in base_message:
        return ""
    return f"\n\n{extra}" if base_message.strip() else extra
