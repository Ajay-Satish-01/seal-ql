"""Chat service guardrails integration (refusal path skips SQL)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from seal_core.chat.service import ChatService
from seal_core.chat.sessions import SessionStore
from seal_core.guardrails.models import ScopeResult
from seal_core.schema.models import DatabaseSchema


@pytest.mark.asyncio
async def test_run_turn_out_of_scope_skips_execute_path() -> None:
    planner = MagicMock()
    executor = MagicMock()
    service = ChatService(
        planner=planner,
        executor=executor,
        sessions=SessionStore(),
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )
    schema = DatabaseSchema(dialect="postgres", tables=[])
    refusal = MagicMock()
    refusal.message = "I only answer data questions."
    refusal.session_id = "s1"
    refusal.sources = []
    refusal.sql = None
    refusal.results = None
    refusal.columns = None
    refusal.chart = None
    refusal.metadata = {"refusal": True}

    with (
        patch(
            "seal_core.chat.service.classify_scope",
            new=AsyncMock(
                return_value=ScopeResult(
                    in_scope=False,
                    reason="off-topic",
                    source="heuristic",
                )
            ),
        ),
        patch.object(service, "_refusal_turn", new=AsyncMock(return_value=refusal)),
        patch.object(service, "_execute_data_path", new=AsyncMock()) as execute_mock,
    ):
        ctx = service._prepare_turn(
            "write me a poem",
            None,
            None,
            None,
            schema,
        )
        result = await service._run_turn(ctx, include_charts=True)

    execute_mock.assert_not_called()
    assert result.sql is None
    assert result.metadata.get("refusal") is True
