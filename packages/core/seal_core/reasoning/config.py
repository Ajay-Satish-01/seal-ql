"""Reasoning feature-flag resolution (env + workspace overrides)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from seal_core.settings import get_settings

RouteKind = Literal["chat", "query"]


@dataclass(frozen=True)
class ReasoningConfig:
    """Effective reasoning toggles for a request."""

    enabled: bool
    clarification_enabled: bool
    inferred_context_enabled: bool
    analysis_followups_enabled: bool
    research_notes_enabled: bool


def resolve_reasoning_config(route: RouteKind) -> ReasoningConfig:
    """Resolve reasoning flags from global settings and per-route toggles."""
    settings = get_settings()
    global_on = settings.reasoning_enabled
    route_on = (
        settings.reasoning_chat_enabled if route == "chat" else settings.reasoning_query_enabled
    )
    enabled = global_on and route_on
    # Chat answer LLM owns follow-ups and research notes; query uses post layers.
    post_layers_on_query = route == "query"
    return ReasoningConfig(
        enabled=enabled,
        clarification_enabled=enabled and settings.reasoning_clarification_enabled,
        inferred_context_enabled=enabled and route == "chat",
        analysis_followups_enabled=(
            enabled and settings.reasoning_analysis_followups_enabled and post_layers_on_query
        ),
        research_notes_enabled=(
            enabled and settings.reasoning_research_notes_enabled and post_layers_on_query
        ),
    )
