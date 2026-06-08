"""Fast-path scope heuristics before LLM classification."""

from __future__ import annotations

import re

# Obvious off-topic or abuse patterns (case-insensitive).
_OFF_TOPIC_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bignore\s+(all\s+)?(previous|prior)\s+instructions\b",
        r"\bjailbreak\b",
        r"\bDAN\s+mode\b",
        r"\bwrite\s+(me\s+)?(a\s+)?(poem|essay|story|song)\b",
        r"\btranslate\s+this\s+paragraph\b",
        r"\bwhat\s+is\s+the\s+capital\s+of\b",
        r"\bwho\s+won\s+the\s+(world\s+cup|super\s+bowl)\b",
    )
)

_DATA_KEYWORDS: frozenset[str] = frozenset(
    {
        "sql",
        "query",
        "table",
        "column",
        "schema",
        "database",
        "chart",
        "aggregate",
        "count",
        "sum",
        "average",
        "trend",
        "join",
        "filter",
        "group",
        "metric",
        "catalog",
        "row",
        "rows",
        "select",
        "data",
        "overview",
        "summary",
        "insights",
        "dashboard",
    }
)


def message_exceeds_max_chars(text: str, max_chars: int) -> bool:
    """Fast length check before LLM classification (mirrors scope limits)."""
    return len(text) > max_chars


def heuristic_in_scope(text: str) -> bool | None:
    """Return True/False for obvious cases, or None to defer to LLM."""
    stripped = text.strip()
    if not stripped:
        return False

    lower = stripped.lower()
    for pattern in _OFF_TOPIC_PATTERNS:
        if pattern.search(stripped):
            return False

    tokens = {t.lower() for t in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", lower)}
    if tokens & _DATA_KEYWORDS:
        return True

    if any(kw in lower for kw in ("how many", "show me", "list ", "top ", "by month", "per ")):
        return True

    return None


# Plan-compat alias (check_scope_heuristics).
check_scope_heuristics = heuristic_in_scope
