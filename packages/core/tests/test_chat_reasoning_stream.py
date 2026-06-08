"""Chat stream vs JSON reasoning parity tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from seal_core.chat.models import ChatAnswer, ChatAnswerEnrichment, ChatDecision
from seal_core.chat.service import ChatService
from seal_core.chat.session import InMemorySessionStore
from seal_core.database.registry import DatabaseBundle, DatabaseRegistry
from seal_core.guardrails.models import ScopeResult
from seal_core.pipeline.execute import ExecuteQueryResult
from seal_core.planner.models import ChartType, QueryPlan
from seal_core.settings import clear_settings_cache
from seal_sql.result import ColumnMetadata


def _registry() -> DatabaseRegistry:
    introspector = MagicMock()
    introspector.introspect = AsyncMock(return_value=MagicMock(tables=[], dialect="postgres"))
    return DatabaseRegistry(
        {
            "default": DatabaseBundle(
                database_id="default",
                dialect="postgres",
                url="mock://",
                introspector=introspector,
                executor=MagicMock(),
            )
        }
    )


def _service() -> ChatService:
    return ChatService(
        planner=MagicMock(),
        registry=_registry(),
        sessions=InMemorySessionStore(),
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )


def _exec_result() -> ExecuteQueryResult:
    return ExecuteQueryResult(
        sql="SELECT COUNT(*) AS n FROM orders",
        columns=[ColumnMetadata("n", "int8")],
        rows=[{"n": 10}],
        plan=QueryPlan(
            sql="SELECT COUNT(*) AS n FROM orders",
            chart_type=ChartType.TABLE,
            title="Orders",
            explanation="count",
        ),
        row_count=1,
        execution_time_ms=2.0,
        truncated=False,
    )


@pytest.fixture(autouse=True)
def _reasoning_on(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv("REASONING_ENABLED", "true")
    monkeypatch.setenv("REASONING_CLARIFICATION_ENABLED", "true")


@pytest.mark.asyncio
async def test_chat_clarification_skips_decision_llm() -> None:
    service = _service()
    with (
        patch(
            "seal_core.chat.service.classify_scope",
            new=AsyncMock(
                return_value=ScopeResult(in_scope=True, reason="in_scope", source="heuristic")
            ),
        ),
        patch.object(service, "_chat_decision", new=AsyncMock()) as decision_mock,
    ):
        result = await service.handle_json(
            message="show me trends",
            session_id=None,
            messages_override=None,
            include_charts=False,
            enhancement_enabled=False,
        )

    decision_mock.assert_not_called()
    assert result.metadata.get("reasoning", {}).get("clarification_required") is True
    assert result.metadata.get("used_sql") is False


@pytest.mark.asyncio
async def test_chat_clarification_does_not_pin_database() -> None:
    """handle_json must not pin the session database on clarification-only turns."""
    store = InMemorySessionStore()
    service = ChatService(
        planner=MagicMock(),
        registry=_registry(),
        sessions=store,
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )
    with patch(
        "seal_core.chat.service.classify_scope",
        new=AsyncMock(
            return_value=ScopeResult(in_scope=True, reason="in_scope", source="heuristic")
        ),
    ):
        result = await service.handle_json(
            message="show me trends",
            session_id=None,
            messages_override=None,
            include_charts=False,
            enhancement_enabled=False,
        )

    assert result.metadata.get("clarification_only") is True
    state = await store.get_session(result.session_id)
    assert state is not None
    assert state.database_id is None


@pytest.mark.asyncio
async def test_chat_specific_query_does_not_probe_schema_for_clarification() -> None:
    service = _service()
    exec_result = _exec_result()
    with (
        patch(
            "seal_core.chat.service.classify_scope",
            new=AsyncMock(
                return_value=ScopeResult(in_scope=True, reason="in_scope", source="heuristic")
            ),
        ),
        patch.object(
            service,
            "_ensure_schema",
            new=AsyncMock(),
        ) as ensure_schema_mock,
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
            new=AsyncMock(
                return_value=ChatAnswer(
                    message="Ten orders.",
                    analysis_followups=["Break down by region"],
                )
            ),
        ),
    ):
        await service.handle_json(
            message="How many orders last month?",
            session_id=None,
            messages_override=None,
            include_charts=False,
            enhancement_enabled=False,
        )
    ensure_schema_mock.assert_not_called()


@pytest.mark.asyncio
async def test_json_explainability_matches_response_reasoning() -> None:
    service = _service()
    exec_result = _exec_result()
    full_answer = ChatAnswer(
        message="Ten orders total.",
        analysis_followups=["Compare by region"],
        research_notes=["Ten orders returned."],
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
            new=AsyncMock(return_value=(exec_result, None, {"used_sql": True})),
        ),
        patch.object(service, "_answer_system", new=AsyncMock(return_value="SYS")),
        patch.object(
            service._client.chat.completions,
            "create",
            new=AsyncMock(return_value=full_answer),
        ),
    ):
        result = await service.handle_json(
            message="How many orders last month?",
            session_id=None,
            messages_override=None,
            include_charts=False,
            enhancement_enabled=False,
        )

    assert result.metadata["reasoning"]["analysis_followups"] == ["Compare by region"]
    _sid, state = await service._sessions.get_or_create(result.session_id)
    messages = state.messages
    assert messages[-1].explainability is not None
    assert messages[-1].explainability.metadata.get("reasoning", {}).get("analysis_followups") == [
        "Compare by region"
    ]


@pytest.mark.asyncio
async def test_stream_emits_final_reasoning_meta_and_suffix() -> None:
    service = _service()
    exec_result = _exec_result()
    enrichment = ChatAnswerEnrichment(
        analysis_followups=["Compare by region"],
        research_notes=["Ten orders returned."],
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
            new=AsyncMock(return_value=(exec_result, None, {"used_sql": True})),
        ),
        patch.object(service, "_answer_system", new=AsyncMock(return_value="SYS")),
        patch(
            "seal_core.chat.service.litellm.acompletion",
            new=AsyncMock(
                return_value=_async_stream_chunks(["Ten orders total."]),
            ),
        ),
        patch.object(
            service._client.chat.completions,
            "create",
            new=AsyncMock(return_value=enrichment),
        ),
    ):
        ctx = await service.prepare_stream_turn(
            message="How many orders last month?",
            session_id=None,
            messages_override=None,
            enhancement_enabled=False,
        )
        events = [
            chunk
            async for chunk in service.stream_turn(
                ctx,
                message=ctx.user_message,
                include_charts=False,
            )
        ]

    meta_events = [e for e in events if e.startswith("event: seal.meta")]
    assert len(meta_events) == 2
    final_meta = meta_events[-1]
    assert '"analysis_followups"' in final_meta
    assert "Compare by region" in final_meta
    assert any("Suggested follow-ups" in e for e in events if e.startswith("data:"))


class _AsyncStream:
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    def __aiter__(self):
        return self

    async def __anext__(self) -> MagicMock:
        if not self._chunks:
            raise StopAsyncIteration
        text = self._chunks.pop(0)
        chunk = MagicMock()
        chunk.choices = [MagicMock(delta=MagicMock(content=text))]
        return chunk


def _async_stream_chunks(chunks: list[str]) -> _AsyncStream:
    return _AsyncStream(chunks)
