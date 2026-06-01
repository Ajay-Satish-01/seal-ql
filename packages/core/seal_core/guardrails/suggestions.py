"""Heuristic in-scope query suggestions for guardrails refusals (no extra LLM on query path)."""

from __future__ import annotations

from seal_core.guardrails.models import ScopeCategory, ScopeResult

_MAX_SUGGESTIONS = 3
_MAX_SUGGESTION_CHARS = 200

_DEFAULT: tuple[str, ...] = (
    "Show order count by month",
    "What tables are available?",
    "List top customers by revenue",
)

_OFF_TOPIC: tuple[str, ...] = (
    "Show order count by month",
    "What tables are available?",
    "Describe the orders table schema",
)

_ABUSE: tuple[str, ...] = (
    "How many orders were placed last month?",
    "What columns does the orders table have?",
    "Show revenue trends by month",
)

_LIMITS: tuple[str, ...] = (
    "Show order count by month",
    "What tables are in the catalog?",
)

_AMBIGUOUS: tuple[str, ...] = (
    "Show order count by month",
    "What metrics can I query?",
    "List available tables",
)


def suggest_queries(scope: ScopeResult) -> list[str]:
    """Return up to three example data questions for an out-of-scope classification."""
    if scope.source == "limits":
        return list(_LIMITS[:_MAX_SUGGESTIONS])

    if scope.category == ScopeCategory.ABUSE:
        return list(_ABUSE[:_MAX_SUGGESTIONS])
    if scope.category == ScopeCategory.OFF_TOPIC:
        return list(_OFF_TOPIC[:_MAX_SUGGESTIONS])
    if scope.category == ScopeCategory.AMBIGUOUS:
        return list(_AMBIGUOUS[:_MAX_SUGGESTIONS])

    reason = (scope.reason or "").lower()
    if any(token in reason for token in ("off-topic", "jailbreak", "injection", "abuse")):
        return list(_ABUSE[:_MAX_SUGGESTIONS])
    if "too long" in reason or "exceeds" in reason:
        return list(_LIMITS[:_MAX_SUGGESTIONS])

    return list(_DEFAULT[:_MAX_SUGGESTIONS])


def _sanitize_suggestion_strings(items: list[str]) -> list[str]:
    cleaned: list[str] = []
    for item in items:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if not text:
            continue
        cleaned.append(text[:_MAX_SUGGESTION_CHARS])
        if len(cleaned) >= _MAX_SUGGESTIONS:
            break
    return cleaned


def merge_suggestions(
    heuristic: list[str],
    llm_suggestions: list[str] | None,
) -> list[str]:
    """Prefer non-empty LLM suggestions; otherwise use heuristics. Cap at three."""
    if llm_suggestions:
        cleaned = _sanitize_suggestion_strings(llm_suggestions)
        if cleaned:
            return cleaned
    return _sanitize_suggestion_strings(heuristic)
