"""Tests for multi-turn clarification conversation helpers."""

from __future__ import annotations

import pytest
from seal_core.chat.models import ChatMessage
from seal_core.intent.conversation import (
    content_for_llm_history,
    effective_user_message,
    is_assistant_clarification,
    is_clarification_follow_up,
    resolve_effective_user_message,
)
from seal_core.reasoning.layers import ClarificationLayer
from seal_core.reasoning.models import DatabaseCapabilities, ReasoningContext, ReasoningPhase


def test_content_for_llm_history_strips_post_answer_suffixes() -> None:
    base = "Ten orders total."
    with_suffix = (
        f"{base}\n\n**Suggested follow-ups**\n"
        "- Compare by region\n\n**Research notes**\n- Ten rows returned."
    )
    assert content_for_llm_history(with_suffix) == base


def test_content_for_llm_history_preserves_clarification_only_body() -> None:
    clarification = "**A few details would help**\n- What time range?"
    assert content_for_llm_history(clarification) == clarification


def test_is_assistant_clarification_detects_reasoning_headers() -> None:
    text = "**A few details would help**\n- What time range?"
    assert is_assistant_clarification(text) is True
    assert is_assistant_clarification("Revenue was highest in the west.") is False


def test_resolve_effective_user_message_merges_clarification_thread() -> None:
    messages = [
        ChatMessage(role="user", content="Which entities rank highest by volume?"),
        ChatMessage(
            role="assistant",
            content="**A few details would help**\n- What time range?",
        ),
        ChatMessage(role="user", content="all history, threshold above 500"),
        ChatMessage(
            role="assistant",
            content="**A few details would help**\n- Which metric?",
        ),
        ChatMessage(role="user", content="records"),
    ]
    resolved = resolve_effective_user_message(messages)
    assert "Which entities rank highest" in resolved
    assert "500" in resolved
    assert "records" in resolved


def test_effective_user_message_falls_back_to_latest_turn() -> None:
    assert effective_user_message(user_message="records", messages=None) == "records"


def test_resolve_effective_user_message_finds_latest_user_when_last_is_assistant() -> None:
    messages = [
        ChatMessage(role="user", content="Show revenue by region"),
        ChatMessage(role="assistant", content="Revenue was highest in the west."),
    ]
    assert resolve_effective_user_message(messages) == "Show revenue by region"


def test_resolve_effective_user_message_merges_when_last_is_clarification() -> None:
    messages = [
        ChatMessage(role="user", content="Which entities rank highest by volume?"),
        ChatMessage(
            role="assistant",
            content="**A few details would help**\n- What time range?",
        ),
        ChatMessage(role="user", content="all history"),
        ChatMessage(
            role="assistant",
            content="**A few details would help**\n- Which metric?",
        ),
    ]
    resolved = resolve_effective_user_message(messages)
    assert "Which entities rank highest" in resolved
    assert "all history" in resolved


def test_resolve_effective_user_message_returns_empty_without_user_turn() -> None:
    messages = [ChatMessage(role="assistant", content="How can I help?")]
    assert resolve_effective_user_message(messages) == ""


def test_is_clarification_follow_up_skips_prior_user_turns() -> None:
    messages = [
        ChatMessage(role="user", content="earlier unrelated question"),
        ChatMessage(role="user", content="Which entities rank highest by volume?"),
        ChatMessage(role="assistant", content="**A few details would help**\n- What time range?"),
        ChatMessage(role="user", content="records"),
    ]
    assert is_clarification_follow_up(messages) is True


def test_is_clarification_follow_up_short_reply_after_clarification() -> None:
    messages = [
        ChatMessage(role="user", content="Which entities rank highest by volume?"),
        ChatMessage(role="assistant", content="**A few details would help**\n- What time range?"),
        ChatMessage(role="user", content="records"),
    ]
    assert is_clarification_follow_up(messages) is True


@pytest.mark.asyncio
async def test_clarification_recognizes_catalog_table_entity_without_schema_load() -> None:
    """Catalog table names must satisfy entity hints even when introspected schema is empty."""
    layer = ClarificationLayer()
    ctx = ReasoningContext(
        route="chat",
        user_message="alpha",
        database_capabilities=DatabaseCapabilities.from_bundle(
            database_id="default",
            dialect="postgres",
        ),
        phase=ReasoningPhase.PRE_EXECUTION,
        schema_table_count=0,
        schema_table_names=("alpha", "beta", "gamma"),
    )
    result = await layer.run(ctx)
    assert not any("What specific metric" in q for q in result.clarifying_questions)


@pytest.mark.asyncio
async def test_clarification_skips_schema_table_question_for_large_schema() -> None:
    layer = ClarificationLayer()
    ctx = ReasoningContext(
        route="query",
        user_message="give me an overview",
        database_capabilities=DatabaseCapabilities.from_bundle(
            database_id="default",
            dialect="postgres",
        ),
        phase=ReasoningPhase.PRE_EXECUTION,
        schema_table_count=20,
        schema_table_names=("alpha", "beta", "gamma"),
    )
    result = await layer.run(ctx)
    assert not any("table or area" in q.lower() for q in result.clarifying_questions)
