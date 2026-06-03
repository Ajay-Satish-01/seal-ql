"""Chat session history API routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from seal_core.chat.models import ChatMessage
from seal_core.chat.session import InMemorySessionStore
from tests.factory import build_client
from tests.shared import AUTH_HEADERS


@pytest.mark.asyncio
async def test_list_get_delete_sessions(monkeypatch) -> None:
    store = InMemorySessionStore()
    sid = await store.create_session()
    await store.append(sid, ChatMessage(role="user", content="Test session title here"))
    await store.set_database_id(sid, "default")

    client: TestClient = build_client(monkeypatch)
    client.app.state.session_store = store

    listed = client.get("/v1/chat/sessions", headers=AUTH_HEADERS)
    assert listed.status_code == 200
    body = listed.json()
    assert any(s["session_id"] == sid for s in body["sessions"])

    detail = client.get(f"/v1/chat/sessions/{sid}", headers=AUTH_HEADERS)
    assert detail.status_code == 200
    assert detail.json()["messages"][0]["content"] == "Test session title here"

    deleted = client.delete(f"/v1/chat/sessions/{sid}", headers=AUTH_HEADERS)
    assert deleted.status_code == 204

    missing = client.get(f"/v1/chat/sessions/{sid}", headers=AUTH_HEADERS)
    assert missing.status_code == 404


def test_chat_invalid_session_id_returns_404(monkeypatch) -> None:
    from unittest.mock import MagicMock

    from app.dependencies import get_chat_service
    from seal_core.chat.service import ChatService
    from seal_core.database.registry import DatabaseBundle, DatabaseRegistry
    from tests.mocks import MockIntrospector, MockPlanner

    store = InMemorySessionStore()
    service = ChatService(
        planner=MockPlanner(),
        registry=DatabaseRegistry(
            {
                "default": DatabaseBundle(
                    database_id="default",
                    dialect="postgres",
                    url="mock://",
                    introspector=MockIntrospector(),
                    executor=MagicMock(),
                )
            }
        ),
        sessions=store,
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )
    client: TestClient = build_client(monkeypatch)
    client.app.dependency_overrides[get_chat_service] = lambda: service
    response = client.post(
        "/v1/chat",
        json={"message": "Hi", "session_id": "not-a-uuid"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "session_not_found"


def test_invalid_session_id_returns_404(monkeypatch) -> None:
    client: TestClient = build_client(monkeypatch)
    client.app.state.session_store = InMemorySessionStore()

    response = client.get("/v1/chat/sessions/not-a-uuid", headers=AUTH_HEADERS)
    assert response.status_code == 404
    assert response.json()["detail"] == "session_not_found"


def test_chat_json_then_list_session(monkeypatch) -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.dependencies import get_chat_service
    from seal_core.chat.models import ChatAnswer, ChatDecision
    from seal_core.chat.service import ChatService
    from seal_core.database.registry import DatabaseBundle, DatabaseRegistry
    from seal_core.guardrails.models import ScopeResult
    from tests.mocks import MockIntrospector, MockPlanner

    store = InMemorySessionStore()
    registry = DatabaseRegistry(
        {
            "default": DatabaseBundle(
                database_id="default",
                dialect="postgres",
                url="mock://",
                introspector=MockIntrospector(),
                executor=MagicMock(),
            )
        }
    )
    service = ChatService(
        planner=MockPlanner(),
        registry=registry,
        sessions=store,
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
        patch.object(service, "_answer_system", new=AsyncMock(return_value="SYS")),
        patch.object(
            service._client.chat.completions,
            "create",
            new=AsyncMock(return_value=ChatAnswer(message="Ten orders.")),
        ),
    ):
        client: TestClient = build_client(monkeypatch)
        client.app.dependency_overrides[get_chat_service] = lambda: service
        client.app.state.session_store = store

        chat = client.post(
            "/v1/chat",
            json={"message": "How many orders?", "database_id": "default"},
            headers=AUTH_HEADERS,
        )
    assert chat.status_code == 200
    sid = chat.json()["session_id"]

    listed = client.get(
        "/v1/chat/sessions",
        headers=AUTH_HEADERS,
        params={"database_id": "default"},
    )
    assert listed.status_code == 200
    body = listed.json()
    assert any(s["session_id"] == sid for s in body["sessions"])
    assert "has_more" in body

    detail = client.get(f"/v1/chat/sessions/{sid}", headers=AUTH_HEADERS)
    assert detail.status_code == 200
    assert len(detail.json()["messages"]) >= 2
