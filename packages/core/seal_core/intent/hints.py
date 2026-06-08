"""Domain-agnostic intent hints from message text and runtime schema names."""

from __future__ import annotations

import re

SPECIFIC_INTENT_MARKERS: tuple[str, ...] = (
    "count",
    "how many",
    "total",
    "sum",
    "average",
    "avg",
    "list",
    "show",
    "top",
    "bottom",
    "highest",
    "lowest",
    "breakdown",
    "group",
    "per",
)

_COMMON_SUFFIXES = r"(?:s|ed|ing|er)?"


def _marker_pattern(marker: str) -> re.Pattern[str]:
    stripped = marker.strip()
    if " " in stripped:
        return re.compile(rf"\b{re.escape(stripped)}\b")
    if stripped == "per":
        return re.compile(r"\bper(?:[-.])?\b")
    return re.compile(rf"\b{re.escape(stripped)}{_COMMON_SUFFIXES}\b")


SPECIFIC_INTENT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    _marker_pattern(marker) for marker in SPECIFIC_INTENT_MARKERS
)


def has_specific_intent(lower: str) -> bool:
    """True when the lowercased message contains a concrete analytical verb/noun."""
    return any(pattern.search(lower) for pattern in SPECIFIC_INTENT_PATTERNS)


def has_table_hint(lower: str, table_names: tuple[str, ...] | list[str] = ()) -> bool:
    """True when the message references a known schema or catalog table name."""
    if not table_names:
        return False
    stems = [re.escape(n.lower().strip()) for n in table_names if n.strip()]
    if not stems:
        return False
    combined = re.compile(rf"\b(?:{'|'.join(stems)}){_COMMON_SUFFIXES}\b")
    return bool(combined.search(lower))
