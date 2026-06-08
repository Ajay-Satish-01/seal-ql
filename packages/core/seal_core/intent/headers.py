"""Shared section headers for reasoning layers and clarification threads."""

from __future__ import annotations

CLARIFICATION_SECTION_HEADERS: tuple[str, ...] = (
    "**A few details would help**",
    "**Clarifying questions**",
)

POST_ANSWER_REASONING_HEADERS: tuple[str, ...] = (
    "**Context from our conversation**",
    "**Research notes**",
    "**Suggested follow-ups**",
)

REASONING_SECTION_HEADERS: tuple[str, ...] = (
    POST_ANSWER_REASONING_HEADERS[0],
    *CLARIFICATION_SECTION_HEADERS,
    *POST_ANSWER_REASONING_HEADERS[1:],
)
