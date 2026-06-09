"""Fast-path scope heuristics before LLM classification."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from seal_core.intent import has_table_hint
from seal_core.intent.conversation import (
    is_clarification_follow_up,
    resolve_effective_user_message,
)
from seal_core.intent.markers import GENERIC_ANALYTICS_KEYWORDS

if TYPE_CHECKING:
    from seal_core.chat.models import ChatMessage

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

_STRONG_DATA_KEYWORDS: frozenset[str] = frozenset(
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
    }
)

_DATA_ACTION_KEYWORDS: frozenset[str] = frozenset(
    {
        "fetch",
        "report",
        "analyze",
        "analyse",
        "calculate",
        "compare",
        "rank",
    }
)

_DATA_ACTION_PHRASES: tuple[str, ...] = (
    "how many",
    "show me",
    "list ",
    "top ",
    "by month",
    "per ",
)


def message_exceeds_max_chars(text: str, max_chars: int) -> bool:
    """Fast length check before LLM classification (mirrors scope limits)."""
    return len(text) > max_chars


def _tokenize(lower: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", lower)}


def _has_data_action_signal(lower: str, tokens: set[str]) -> bool:
    if tokens & _DATA_ACTION_KEYWORDS:
        return True
    return any(phrase in lower for phrase in _DATA_ACTION_PHRASES)


def heuristic_in_scope(text: str) -> bool | None:
    """Return True/False for obvious cases, or None to defer to LLM."""
    stripped = text.strip()
    if not stripped:
        return False

    lower = stripped.lower()
    for pattern in _OFF_TOPIC_PATTERNS:
        if pattern.search(stripped):
            return False

    tokens = _tokenize(lower)
    if tokens & _STRONG_DATA_KEYWORDS:
        return True

    has_action = _has_data_action_signal(lower, tokens)
    if tokens & GENERIC_ANALYTICS_KEYWORDS:
        return True if has_action else None

    if has_action:
        return True

    return None


def heuristic_in_scope_with_context(
    text: str,
    *,
    prior_messages: tuple[ChatMessage, ...] | list[ChatMessage] | None = None,
    schema_table_names: tuple[str, ...] | list[str] = (),
) -> bool | None:
    """Scope heuristic that considers clarification threads and schema entity names."""
    base = heuristic_in_scope(text)
    if base is not None:
        return base

    if schema_table_names and has_table_hint(text.strip().lower(), table_names=schema_table_names):
        return True

    if prior_messages:
        if is_clarification_follow_up(prior_messages):
            resolved = resolve_effective_user_message(prior_messages)
            if resolved:
                resolved_hint = heuristic_in_scope(resolved)
                if resolved_hint is not None:
                    return resolved_hint
                if schema_table_names and has_table_hint(
                    resolved.strip().lower(),
                    table_names=schema_table_names,
                ):
                    return True
            return None

        resolved = resolve_effective_user_message(prior_messages)
        if resolved and resolved.strip() != text.strip():
            return heuristic_in_scope(resolved)

    return None


# Plan-compat alias (check_scope_heuristics).
check_scope_heuristics = heuristic_in_scope
