"""Shared lexical markers for scope heuristics and clarification layers."""

from __future__ import annotations

# Vague analytics phrasing — defer scope unless paired with a data-action signal.
GENERIC_ANALYTICS_KEYWORDS: frozenset[str] = frozenset(
    {
        "overview",
        "summary",
        "insights",
        "dashboard",
    }
)

# Underspecified question phrasing used by clarification heuristics.
VAGUE_QUESTION_MARKERS: tuple[str, ...] = tuple(marker for marker in GENERIC_ANALYTICS_KEYWORDS) + (
    "show me",
    "tell me",
    "what about",
    "how are",
)
