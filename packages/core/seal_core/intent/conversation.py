"""Multi-turn helpers for clarification threads and resolved user intent."""

from __future__ import annotations

from typing import TYPE_CHECKING

from seal_core.intent.headers import CLARIFICATION_SECTION_HEADERS, POST_ANSWER_REASONING_HEADERS

if TYPE_CHECKING:
    from seal_core.chat.models import ChatMessage

# Short replies in a clarification thread are rarely standalone questions.
_CLARIFICATION_FOLLOW_UP_MAX_CHARS = 120
_CLARIFICATION_FOLLOW_UP_MAX_WORDS = 16


def is_assistant_clarification(content: str) -> bool:
    """True when assistant text is a clarification-only response."""
    return any(header in content for header in CLARIFICATION_SECTION_HEADERS)


def content_for_llm_history(content: str) -> str:
    """Strip post-answer reasoning suffixes; keep clarification-only bodies intact."""
    if is_assistant_clarification(content):
        return content
    cut_at = len(content)
    for header in POST_ANSWER_REASONING_HEADERS:
        idx = content.find(header)
        if idx >= 0:
            cut_at = min(cut_at, idx)
    return content[:cut_at].strip()


def is_clarification_follow_up(messages: tuple[ChatMessage, ...] | list[ChatMessage]) -> bool:
    """True when the latest user turn answers a prior clarification prompt."""
    if len(messages) < 2:
        return False
    if messages[-1].role != "user":
        return False
    current = messages[-1].content.strip()
    if not current:
        return False
    if (
        len(current) > _CLARIFICATION_FOLLOW_UP_MAX_CHARS
        or len(current.split()) > _CLARIFICATION_FOLLOW_UP_MAX_WORDS
    ):
        return False
    for msg in reversed(messages[:-1]):
        if msg.role == "assistant":
            return is_assistant_clarification(msg.content)
    return False


def effective_user_message(
    *,
    user_message: str,
    messages: tuple[ChatMessage, ...] | list[ChatMessage] | None = None,
) -> str:
    """Resolved intent from a clarification thread, or the latest user message."""
    if messages:
        resolved = resolve_effective_user_message(messages)
        if resolved:
            return resolved
    return user_message.strip()


def _collect_clarification_thread_users(
    messages: tuple[ChatMessage, ...] | list[ChatMessage],
) -> list[str]:
    """User turns merged backward through clarification-only assistant prompts."""
    collected: list[str] = []
    i = len(messages) - 1
    while i >= 0:
        msg = messages[i]
        if msg.role == "assistant" and is_assistant_clarification(msg.content):
            i -= 1
        elif msg.role == "user":
            part = msg.content.strip()
            if part:
                collected.insert(0, part)
            i -= 1
        else:
            break
    return collected


def _join_user_parts(parts: list[str]) -> str:
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return " | ".join(parts)


def resolve_effective_user_message(messages: tuple[ChatMessage, ...] | list[ChatMessage]) -> str:
    """Merge user turns in an active clarification thread into one intent string."""
    if not messages:
        return ""
    if messages[-1].role != "user":
        if messages[-1].role == "assistant" and is_assistant_clarification(messages[-1].content):
            return _join_user_parts(_collect_clarification_thread_users(messages))
        for msg in reversed(messages):
            if msg.role == "user":
                return msg.content.strip()
        return ""
    return _join_user_parts(_collect_clarification_thread_users(messages))
