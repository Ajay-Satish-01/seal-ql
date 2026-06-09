"""Transport-agnostic intent resolution shared by guardrails and reasoning."""

from seal_core.intent.conversation import (
    content_for_llm_history,
    effective_user_message,
    is_assistant_clarification,
    is_clarification_follow_up,
    resolve_effective_user_message,
)
from seal_core.intent.hints import has_specific_intent, has_table_hint
from seal_core.intent.markers import GENERIC_ANALYTICS_KEYWORDS, VAGUE_QUESTION_MARKERS

__all__ = [
    "GENERIC_ANALYTICS_KEYWORDS",
    "VAGUE_QUESTION_MARKERS",
    "content_for_llm_history",
    "effective_user_message",
    "has_specific_intent",
    "has_table_hint",
    "is_assistant_clarification",
    "is_clarification_follow_up",
    "resolve_effective_user_message",
]
