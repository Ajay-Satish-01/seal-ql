"""Policy regression tests for ambiguity/clarification (eval-runner complement)."""

from __future__ import annotations

import pytest
from seal_core.reasoning.layers import ClarificationLayer
from seal_core.reasoning.models import DatabaseCapabilities, ReasoningContext, ReasoningPhase

_AMBIGUOUS_QUERIES = (
    "show me trends",
    "How is it performing compared to that period?",
)

_SPECIFIC_QUERIES = (
    "How many orders were placed last month?",
    "top orders",
)


@pytest.mark.parametrize("question", _AMBIGUOUS_QUERIES)
@pytest.mark.asyncio
async def test_ambiguous_queries_request_clarification(question: str) -> None:
    layer = ClarificationLayer()
    ctx = ReasoningContext(
        route="query",
        user_message=question,
        database_capabilities=DatabaseCapabilities.from_bundle(
            database_id="default",
            dialect="postgres",
        ),
        phase=ReasoningPhase.PRE_EXECUTION,
    )
    result = await layer.run(ctx)
    assert result.clarification_required is True
    assert result.clarifying_questions


@pytest.mark.parametrize("question", _SPECIFIC_QUERIES)
@pytest.mark.asyncio
async def test_specific_queries_skip_clarification(question: str) -> None:
    layer = ClarificationLayer()
    ctx = ReasoningContext(
        route="query",
        user_message=question,
        database_capabilities=DatabaseCapabilities.from_bundle(
            database_id="default",
            dialect="postgres",
        ),
        phase=ReasoningPhase.PRE_EXECUTION,
    )
    result = await layer.run(ctx)
    assert result.clarification_required is False
