"""Chat service metadata parity when SQL runs."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from seal_core.chat.models import ChatAnswer, ChatDecision
from seal_core.chat.service import ChatService
from seal_core.chat.sessions import SessionStore
from seal_core.database.registry import DatabaseBundle, DatabaseRegistry
from seal_core.guardrails.models import ScopeResult
from seal_core.pipeline.execute import ExecuteQueryResult
from seal_core.planner.models import ChartType, QueryPlan
from seal_sql.result import ColumnMetadata


def _registry() -> DatabaseRegistry:
    introspector = MagicMock()
    introspector.introspect = AsyncMock(return_value=MagicMock(tables=[], dialect="postgres"))
    executor = MagicMock()
    return DatabaseRegistry(
        {
            "default": DatabaseBundle(
                database_id="default",
                dialect="postgres",
                url="mock://",
                introspector=introspector,
                executor=executor,
            )
        }
    )


def _exec_result() -> ExecuteQueryResult:
    return ExecuteQueryResult(
        sql="SELECT COUNT(*) AS n FROM orders",
        columns=[ColumnMetadata("n", "int8")],
        rows=[{"n": 42}],
        plan=QueryPlan(
            sql="SELECT COUNT(*) AS n FROM orders",
            chart_type=ChartType.TABLE,
            title="Orders",
            explanation="count",
        ),
        row_count=1,
        execution_time_ms=3.2,
        truncated=False,
        warnings=[],
        repair_attempts=1,
    )


@pytest.mark.asyncio
async def test_run_turn_sql_metadata_includes_execution_fields() -> None:
    service = ChatService(
        planner=MagicMock(),
        registry=_registry(),
        sessions=SessionStore(),
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )
    exec_result = _exec_result()
    answer = ChatAnswer(message="There are 42 orders.")

    with (
        patch(
            "seal_core.chat.service.classify_scope",
            new=AsyncMock(
                return_value=ScopeResult(in_scope=True, reason="in_scope", source="heuristic")
            ),
        ),
        patch.object(
            service,
            "_chat_decision",
            new=AsyncMock(return_value=ChatDecision(needs_data=True, confidence="high")),
        ),
        patch.object(
            service,
            "_execute_data_path",
            new=AsyncMock(return_value=(exec_result, None, {"used_sql": True})),
        ),
        patch.object(service, "_answer_system", new=AsyncMock(return_value="SYS")),
        patch.object(
            service._client.chat.completions,
            "create",
            new=AsyncMock(return_value=answer),
        ),
    ):
        ctx = service._prepare_turn("How many orders?", None, None, None, "default")
        result = await service._run_turn(ctx, include_charts=False)

    meta = result.metadata
    assert meta["used_sql"] is True
    assert meta["row_count"] == 1
    assert meta["execution_time_ms"] == 3.2
    assert meta["repair_attempts"] == 1
    assert meta["database_id"] == "default"
    assert meta["enhancement"]["enabled"] is False
    assert meta["enhancement"]["applied"] == []
    assert result.columns == [{"name": "n", "type": "int8", "nullable": True}]


@pytest.mark.asyncio
async def test_run_turn_sql_error_metadata() -> None:
    service = ChatService(
        planner=MagicMock(),
        registry=_registry(),
        sessions=SessionStore(),
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )

    with (
        patch(
            "seal_core.chat.service.classify_scope",
            new=AsyncMock(
                return_value=ScopeResult(in_scope=True, reason="in_scope", source="heuristic")
            ),
        ),
        patch.object(
            service,
            "_chat_decision",
            new=AsyncMock(return_value=ChatDecision(needs_data=True, confidence="high")),
        ),
        patch.object(
            service,
            "_execute_data_path",
            new=AsyncMock(return_value=(None, None, {"sql_error": True})),
        ),
        patch.object(service, "_answer_system", new=AsyncMock(return_value="SYS")),
        patch.object(
            service._client.chat.completions,
            "create",
            new=AsyncMock(return_value=ChatAnswer(message="Could not query data.")),
        ),
    ):
        ctx = service._prepare_turn("broken query", None, None, None, "default")
        result = await service._run_turn(ctx, include_charts=False)

    assert result.sql is None
    assert result.metadata["used_sql"] is False
    assert result.metadata["sql_error"] is True
    assert result.metadata["row_count"] == 0


@pytest.mark.asyncio
async def test_run_turn_no_sql_when_decision_skips_data() -> None:
    service = ChatService(
        planner=MagicMock(),
        registry=_registry(),
        sessions=SessionStore(),
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )

    with (
        patch(
            "seal_core.chat.service.classify_scope",
            new=AsyncMock(
                return_value=ScopeResult(in_scope=True, reason="in_scope", source="heuristic")
            ),
        ),
        patch.object(
            service,
            "_chat_decision",
            new=AsyncMock(return_value=ChatDecision(needs_data=False, confidence="high")),
        ),
        patch.object(service, "_execute_data_path", new=AsyncMock()) as execute_mock,
        patch.object(service, "_answer_system", new=AsyncMock(return_value="SYS")),
        patch.object(
            service._client.chat.completions,
            "create",
            new=AsyncMock(return_value=ChatAnswer(message="General answer.")),
        ),
    ):
        ctx = service._prepare_turn("hello", None, None, None, "default")
        result = await service._run_turn(ctx, include_charts=False)

    execute_mock.assert_not_called()
    assert result.metadata["used_sql"] is False
    assert "enhancement" in result.metadata


@pytest.mark.asyncio
async def test_format_meta_event_includes_execution_fields() -> None:
    from seal_core.chat.service import InScopeTurnData

    service = ChatService(
        planner=MagicMock(),
        registry=_registry(),
        sessions=SessionStore(),
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )
    exec_result = _exec_result()
    ctx = service._prepare_turn("count orders", None, None, None, "analytics")
    ctx.metadata["sources"] = ["orders"]
    ctx.metadata["scope"] = {"in_scope": True, "reason": "in_scope", "source": "heuristic"}
    turn = InScopeTurnData(exec_result=exec_result, chart=None, meta={}, system="SYS")

    event_line = service._format_meta_event(ctx, turn)
    assert event_line.startswith("event: seal.meta")
    assert '"repair_attempts": 1' in event_line
    assert '"row_count": 1' in event_line
    assert '"database_id": "analytics"' in event_line
    assert "vector_skipped_reason" not in event_line


@pytest.mark.asyncio
async def test_format_meta_event_sql_error_flag() -> None:
    from seal_core.chat.service import InScopeTurnData

    service = ChatService(
        planner=MagicMock(),
        registry=_registry(),
        sessions=SessionStore(),
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )
    ctx = service._prepare_turn("broken", None, None, None, "default")
    turn = InScopeTurnData(exec_result=None, chart=None, meta={"sql_error": True}, system="SYS")

    event_line = service._format_meta_event(ctx, turn)
    compact = event_line.replace(" ", "")
    assert '"sql_error":true' in compact
    assert '"used_sql":false' in compact


@pytest.mark.asyncio
async def test_format_meta_event_vector_skipped_when_enhancement_enabled() -> None:
    from seal_core.chat.service import InScopeTurnData

    service = ChatService(
        planner=MagicMock(),
        registry=_registry(),
        sessions=SessionStore(),
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )
    exec_result = _exec_result()
    ctx = service._prepare_turn("count orders", None, None, None, "analytics")
    ctx.enhancement_enabled = True
    turn = InScopeTurnData(exec_result=exec_result, chart=None, meta={}, system="SYS")

    event_line = service._format_meta_event(ctx, turn)
    assert '"vector_skipped_reason": "non_default_database"' in event_line


@pytest.mark.asyncio
async def test_refusal_metadata_omits_vector_skipped_on_non_default() -> None:
    service = ChatService(
        planner=MagicMock(),
        registry=_registry(),
        sessions=SessionStore(),
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )

    with patch(
        "seal_core.chat.service.classify_scope",
        new=AsyncMock(
            return_value=ScopeResult(in_scope=False, reason="off-topic", source="heuristic")
        ),
    ):
        ctx = service._prepare_turn("poem", None, None, False, "analytics")
        result = await service._refusal_turn(
            ctx,
            scope=ScopeResult(in_scope=False, reason="too long", source="limits"),
        )

    assert result.metadata["refusal"] is True
    assert "vector_skipped_reason" not in result.metadata.get("enhancement", {})


@pytest.mark.asyncio
async def test_refusal_metadata_omits_unavailable_when_orchestrator_present() -> None:
    from seal_core.enhancement.orchestrator import EnhancementOrchestrator
    from seal_core.enhancement.vector_rag import VectorRagEnhancer
    from seal_core.vector.noop_store import NoopVectorStore

    orchestrator = EnhancementOrchestrator([VectorRagEnhancer(NoopVectorStore())])
    service = ChatService(
        planner=MagicMock(),
        registry=_registry(),
        sessions=SessionStore(),
        orchestrator=orchestrator,
        catalog=None,
        semantic_registry=None,
    )

    with patch(
        "seal_core.chat.service.classify_scope",
        new=AsyncMock(
            return_value=ScopeResult(in_scope=False, reason="off-topic", source="heuristic")
        ),
    ):
        ctx = service._prepare_turn(
            "write me a poem",
            None,
            None,
            True,
            "default",
        )
        result = await service._refusal_turn(
            ctx,
            scope=ScopeResult(in_scope=False, reason="off-topic", source="heuristic"),
        )

    assert result.metadata["refusal"] is True
    assert result.metadata["enhancement"]["enabled"] is False
    assert "unavailable_reason" not in result.metadata.get("enhancement", {})
