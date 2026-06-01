"""API tests for chat refusal and enhancement metadata."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.dependencies import get_chat_service, get_database_registry
from fastapi.testclient import TestClient
from seal_core.chat.service import ChatService
from seal_core.chat.sessions import SessionStore
from seal_core.guardrails.models import ScopeResult
from seal_core.pipeline.models import ENHANCEMENT_UNAVAILABLE_ORCHESTRATOR
from tests.factory import build_client
from tests.mocks import MockIntrospector, MockPlanner
from tests.shared import AUTH_HEADERS


def test_chat_refusal_reports_unavailable_when_enhancement_requested_without_orchestrator(
    monkeypatch,
) -> None:
    from seal_core.database.registry import DatabaseBundle, DatabaseRegistry

    registry = DatabaseRegistry(
        {
            "default": DatabaseBundle(
                database_id="default",
                dialect="postgres",
                url="mock://",
                introspector=MockIntrospector(),
                executor=AsyncMock(),
            )
        }
    )
    service = ChatService(
        planner=MockPlanner(),
        registry=registry,
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
        client: TestClient = build_client(monkeypatch)
        client.app.dependency_overrides[get_chat_service] = lambda: service
        client.app.dependency_overrides[get_database_registry] = lambda: registry
        r = client.post(
            "/v1/chat",
            json={"message": "write a poem", "enhancement": True},
            headers=AUTH_HEADERS,
        )

    assert r.status_code == 200
    enh = r.json()["metadata"]["enhancement"]
    assert enh["unavailable_reason"] == ENHANCEMENT_UNAVAILABLE_ORCHESTRATOR
    assert enh["enabled"] is False
