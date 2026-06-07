"""Shared heuristic constants for reasoning layers and clarification probing."""

from __future__ import annotations

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
    "per ",
)

TABLE_HINT_MARKERS: tuple[str, ...] = (
    "order",
    "customer",
    "product",
    "user",
    "event",
)

LARGE_SCHEMA_THRESHOLD = 8


def has_specific_intent(lower: str) -> bool:
    """True when the lowercased message contains a concrete analytical verb/noun."""
    return any(marker in lower for marker in SPECIFIC_INTENT_MARKERS)


def has_table_hint(lower: str) -> bool:
    """True when the lowercased message names a recognizable business entity."""
    return any(marker in lower for marker in TABLE_HINT_MARKERS)
