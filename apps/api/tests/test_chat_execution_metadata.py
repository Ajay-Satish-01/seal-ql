"""API tests for unified chat execution metadata when SQL runs."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.dependencies import get_chat_service
from fastapi.testclient import TestClient
from seal_core.chat.models import ChatAnswer, ChatDecision
from seal_core.chat.service import ChatService
from seal_core.chat.session import InMemorySessionStore
from seal_core.database.registry import DatabaseBundle, DatabaseRegistry
from seal_core.guardrails.models import ScopeResult
from seal_core.pipeline.execute import ExecuteQueryResult
from seal_core.planner.models import ChartType, QueryPlan
from seal_sql.result import ColumnMetadata
from tests.factory import build_client
from tests.mocks import MockIntrospector, MockPlanner
from tests.shared import AUTH_HEADERS, enable_trust_explainability


def _chat_service_with_sql() -> ChatService:
    introspector = MockIntrospector()
    registry = DatabaseRegistry(
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
    return ChatService(
        planner=MockPlanner(),
        registry=registry,
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
        warnings=[],
        repair_attempts=2,
    )


def test_chat_json_metadata_hides_trust_fields_by_default(monkeypatch) -> None:
    service = _chat_service_with_sql()
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
            new=AsyncMock(return_value=ChatAnswer(message="Ten orders.")),
        ),
    ):
        client: TestClient = build_client(monkeypatch)
        client.app.dependency_overrides[get_chat_service] = lambda: service
        r = client.post(
            "/v1/chat",
            json={"message": "How many orders?"},
            headers=AUTH_HEADERS,
        )

    assert r.status_code == 200
    meta = r.json()["metadata"]
    assert meta["used_sql"] is True
    assert "repair_attempts" not in meta
    assert "scope" not in meta
    body = r.json()
    assert body["sql"] is None
    assert body["columns"] is None


def test_chat_json_metadata_when_sql_runs(monkeypatch) -> None:
    enable_trust_explainability(monkeypatch)
    service = _chat_service_with_sql()
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
            new=AsyncMock(return_value=ChatAnswer(message="Ten orders.")),
        ),
    ):
        client: TestClient = build_client(monkeypatch)
        client.app.dependency_overrides[get_chat_service] = lambda: service
        r = client.post(
            "/v1/chat",
            json={"message": "How many orders?"},
            headers=AUTH_HEADERS,
        )

    assert r.status_code == 200
    meta = r.json()["metadata"]
    assert meta["database_id"] == "default"
    assert meta["row_count"] == 1
    assert meta["repair_attempts"] == 2
    assert meta["used_sql"] is True
    assert meta["enhancement"]["enabled"] is False
    assert meta["enhancement"]["applied"] == []
    body = r.json()
    assert body["columns"] == [{"name": "n", "type": "int8", "nullable": True}]


def test_chat_json_sql_error_metadata(monkeypatch) -> None:
    service = _chat_service_with_sql()

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
            new=AsyncMock(return_value=ChatAnswer(message="Could not run that query.")),
        ),
    ):
        client: TestClient = build_client(monkeypatch)
        client.app.dependency_overrides[get_chat_service] = lambda: service
        r = client.post(
            "/v1/chat",
            json={"message": "broken"},
            headers=AUTH_HEADERS,
        )

    assert r.status_code == 200
    meta = r.json()["metadata"]
    assert meta["sql_error"] is True
    assert meta["used_sql"] is False
    assert r.json()["sql"] is None


def test_chat_stream_meta_includes_execution_fields(monkeypatch) -> None:
    enable_trust_explainability(monkeypatch)
    service = _chat_service_with_sql()
    exec_result = _exec_result()

    with (
        patch(
            "seal_core.chat.service.classify_scope",
            new=AsyncMock(
                return_value=ScopeResult(in_scope=True, reason="in_scope", source="heuristic")
            ),
        ),
        patch("seal_core.chat.service.litellm.acompletion", new=_mock_streaming_completion),
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
    ):
        client: TestClient = build_client(monkeypatch)
        client.app.dependency_overrides[get_chat_service] = lambda: service
        with client.stream(
            "POST",
            "/v1/chat",
            json={"message": "count", "stream": True},
            headers=AUTH_HEADERS,
        ) as r:
            text = "".join(r.iter_text())

    assert r.status_code == 200
    meta_line = next(
        line
        for line in text.splitlines()
        if line.startswith("data: {") and "repair_attempts" in line
    )
    payload = json.loads(meta_line[6:])
    assert payload["repair_attempts"] == 2
    assert payload["row_count"] == 1
    assert payload["enhancement"]["applied"] == []


def test_chat_stream_sql_error_meta(monkeypatch) -> None:
    service = _chat_service_with_sql()

    with (
        patch(
            "seal_core.chat.service.classify_scope",
            new=AsyncMock(
                return_value=ScopeResult(in_scope=True, reason="in_scope", source="heuristic")
            ),
        ),
        patch("seal_core.chat.service.litellm.acompletion", new=_mock_streaming_completion),
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
    ):
        client: TestClient = build_client(monkeypatch)
        client.app.dependency_overrides[get_chat_service] = lambda: service
        with client.stream(
            "POST",
            "/v1/chat",
            json={"message": "broken", "stream": True},
            headers=AUTH_HEADERS,
        ) as r:
            text = "".join(r.iter_text())

    assert r.status_code == 200
    meta_line = next(
        line for line in text.splitlines() if line.startswith("data: {") and '"sql_error"' in line
    )
    payload = json.loads(meta_line[6:])
    assert payload["sql_error"] is True
    assert payload["used_sql"] is False
    assert payload.get("sql") is None


async def _mock_streaming_completion(**_kwargs):
    async def _gen():
        chunk = MagicMock()
        chunk.choices = [MagicMock(delta=MagicMock(content="Ten orders."))]
        yield chunk

    return _gen()
