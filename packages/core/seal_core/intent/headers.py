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

# Free-text sections some answer models emit before structured enrichment runs.
INLINE_ANSWER_ENRICHMENT_HEADERS: tuple[str, ...] = (
    "### Suggested analysis_followups",
    "### Suggested follow-ups",
    "### Research_notes",
    "### Research notes",
)

REASONING_SECTION_HEADERS: tuple[str, ...] = (
    POST_ANSWER_REASONING_HEADERS[0],
    *CLARIFICATION_SECTION_HEADERS,
    *POST_ANSWER_REASONING_HEADERS[1:],
)
