"""Backward-compatible re-exports for reasoning-layer intent hints."""

from seal_core.intent.hints import (
    SPECIFIC_INTENT_MARKERS,
    SPECIFIC_INTENT_PATTERNS,
    has_specific_intent,
    has_table_hint,
)

__all__ = [
    "SPECIFIC_INTENT_MARKERS",
    "SPECIFIC_INTENT_PATTERNS",
    "has_specific_intent",
    "has_table_hint",
]
