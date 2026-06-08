"""Default reasoning layers (heuristic + optional LLM enrichment)."""

from __future__ import annotations

import re

from seal_core.intent import has_specific_intent, has_table_hint
from seal_core.intent.markers import VAGUE_QUESTION_MARKERS
from seal_core.reasoning.config import ReasoningConfig, resolve_reasoning_config
from seal_core.reasoning.models import (
    ReasoningContext,
    ReasoningLayerResult,
    ReasoningPhase,
    strip_reasoning_from_content,
)

_AMBIGUOUS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(it|that|those|them|this)\b", re.IGNORECASE),
    re.compile(r"\b(recent|latest|best|top)\b", re.IGNORECASE),
    re.compile(r"\b(compare|compared|trend|growth|performance|performing)\b", re.IGNORECASE),
)

_TIME_RANGE_MARKERS: tuple[str, ...] = (
    "last ",
    "past ",
    "since ",
    "between ",
    "yesterday",
    "today",
    "this week",
    "this month",
    "this year",
    "q1",
    "q2",
    "q3",
    "q4",
)

_TOP_ENTITY_PATTERN = re.compile(
    r"\b(top|best|highest|lowest)\s+\d*\s*\w+",
    re.IGNORECASE,
)


def _extract_prior_topics(messages: tuple | list | None) -> list[str]:
    """Heuristic topic extraction from prior assistant turns."""
    if not messages:
        return []
    topics: list[str] = []
    for msg in messages:
        if getattr(msg, "role", None) != "assistant":
            continue
        content = strip_reasoning_from_content(getattr(msg, "content", "") or "")
        for line in content.splitlines():
            stripped = line.strip().lstrip("-•").strip()
            if 10 <= len(stripped) <= 120:
                topics.append(stripped)
    return topics[-3:]


def _needs_clarification_heuristic(ctx: ReasoningContext) -> tuple[bool, list[str]]:
    """Detect underspecified requests without an extra LLM call."""
    text = ctx.user_message.strip()
    lower = text.lower()
    questions: list[str] = []

    has_specific = has_specific_intent(lower)
    has_schema_entity = has_table_hint(lower, table_names=ctx.schema_table_names)
    if len(text) < 8 and not has_specific and not has_schema_entity:
        questions.append("What specific metric or outcome should I measure?")

    ambiguous_hits = sum(1 for pattern in _AMBIGUOUS_PATTERNS if pattern.search(text))
    pronoun_hits = len(_AMBIGUOUS_PATTERNS[0].findall(text))
    has_time = any(marker in lower for marker in _TIME_RANGE_MARKERS)
    has_vague = any(marker in lower for marker in VAGUE_QUESTION_MARKERS)

    if pronoun_hits >= 1 and ambiguous_hits >= 2:
        questions.append("Which entity or time period does 'it/that' refer to in your question?")
    elif ambiguous_hits >= 3 and not has_specific and not has_schema_entity:
        questions.append("Can you specify the metric, grouping, or time period you have in mind?")

    if (
        has_vague
        and not has_time
        and any(word in lower for word in ("trend", "growth", "compare", "performance"))
        and "all time" not in lower
        and "overall timeline" not in lower
        and "entire history" not in lower
    ):
        questions.append("What time range should I use (e.g. last 30 days, this quarter)?")

    if (
        any(word in lower for word in ("top", "best", "highest", "lowest"))
        and " by " not in lower
        and not _TOP_ENTITY_PATTERN.search(text)
        and not has_schema_entity
        and not has_specific
    ):
        questions.append("What dimension should I rank or group by?")

    deduped = list(dict.fromkeys(q for q in questions if q.strip()))
    return bool(deduped), deduped[:5]


class InferredContextLayer:
    """Infer concise context from prior chat state (chat route only)."""

    name = "inferred_context"
    phase = ReasoningPhase.PRE_EXECUTION

    def __init__(self, config: ReasoningConfig | None = None) -> None:
        self._config = config

    def enabled(self, ctx: ReasoningContext) -> bool:
        cfg = self._config or resolve_reasoning_config(ctx.route)
        return cfg.inferred_context_enabled and ctx.route == "chat"

    async def run(self, ctx: ReasoningContext) -> ReasoningLayerResult:
        prior_topics = ctx.prior_assistant_topics or _extract_prior_topics(ctx.messages)
        if not prior_topics:
            return ReasoningLayerResult(layer_name=self.name)

        inferred = [
            f"Continuing from earlier discussion about: {prior_topics[-1][:100]}",
        ]
        if len(prior_topics) > 1:
            inferred.append(f"Related prior topics: {'; '.join(t[:60] for t in prior_topics[:-1])}")
        return ReasoningLayerResult(
            inferred_context=inferred[:3],
            layer_name=self.name,
        )


class ClarificationLayer:
    """Detect missing requirements and emit clarifying questions."""

    name = "clarification"
    phase = ReasoningPhase.PRE_EXECUTION

    def __init__(self, config: ReasoningConfig | None = None) -> None:
        self._config = config

    def enabled(self, ctx: ReasoningContext) -> bool:
        cfg = self._config or resolve_reasoning_config(ctx.route)
        return cfg.clarification_enabled

    async def run(self, ctx: ReasoningContext) -> ReasoningLayerResult:
        required, questions = _needs_clarification_heuristic(ctx)
        return ReasoningLayerResult(
            clarifying_questions=questions,
            clarification_required=required,
            layer_name=self.name,
        )


class AnalysisFollowupsLayer:
    """Suggest analytical follow-up angles after execution or schema grounding."""

    name = "analysis_followups"
    phase = ReasoningPhase.POST_EXECUTION

    def __init__(self, config: ReasoningConfig | None = None) -> None:
        self._config = config

    def enabled(self, ctx: ReasoningContext) -> bool:
        cfg = self._config or resolve_reasoning_config(ctx.route)
        return cfg.analysis_followups_enabled

    async def run(self, ctx: ReasoningContext) -> ReasoningLayerResult:
        followups: list[str] = []
        lower = ctx.user_message.lower()

        if ctx.exec_result and ctx.exec_result.row_count > 0:
            followups.append("Break this down by segment or category to compare drivers.")
            if ctx.database_capabilities.supports_time_series:
                followups.append("Show the same metric over time to spot trends or seasonality.")
        elif "count" in lower or "how many" in lower:
            followups.append("Compare counts across time periods to see growth or decline.")

        if not followups:
            followups.append("Explore outliers or top contributors for this question.")

        return ReasoningLayerResult(
            analysis_followups=followups[:3],
            layer_name=self.name,
        )


class ResearchNotesLayer:
    """Attach concise data-backed research framing notes."""

    name = "research_notes"
    phase = ReasoningPhase.POST_EXECUTION

    def __init__(self, config: ReasoningConfig | None = None) -> None:
        self._config = config

    def enabled(self, ctx: ReasoningContext) -> bool:
        cfg = self._config or resolve_reasoning_config(ctx.route)
        return cfg.research_notes_enabled

    async def run(self, ctx: ReasoningContext) -> ReasoningLayerResult:
        notes: list[str] = []
        if ctx.exec_result:
            notes.append(
                f"Query returned {ctx.exec_result.row_count} row(s) "
                f"in {ctx.exec_result.execution_time_ms:.1f} ms."
            )
            if ctx.exec_result.truncated:
                notes.append("Results were truncated; consider narrowing filters or adding LIMIT.")
            if ctx.exec_result.tables_used:
                from seal_core.pipeline.trust import is_trust_explainability_enabled

                if is_trust_explainability_enabled():
                    notes.append(
                        f"Data sourced from: {', '.join(ctx.exec_result.tables_used[:5])}."
                    )
        elif ctx.schema_table_count:
            notes.append(
                f"Schema exposes {ctx.schema_table_count} table(s) on "
                f"{ctx.database_capabilities.provider} ({ctx.database_capabilities.dialect})."
            )

        return ReasoningLayerResult(
            research_notes=notes[:3],
            layer_name=self.name,
        )
