"""Backward-compatible re-exports for multi-turn intent resolution."""

from seal_core.intent.conversation import (
    effective_user_message,
    is_assistant_clarification,
    is_clarification_follow_up,
    resolve_effective_user_message,
)

__all__ = [
    "effective_user_message",
    "is_assistant_clarification",
    "is_clarification_follow_up",
    "resolve_effective_user_message",
]
