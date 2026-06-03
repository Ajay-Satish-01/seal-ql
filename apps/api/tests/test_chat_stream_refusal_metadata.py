"""API tests for seal.meta on streamed guardrails refusals (real ChatService)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.dependencies import get_chat_service
from fastapi.testclient import TestClient
from seal_core.chat.models import ChatAnswer
from seal_core.chat.service import ChatService
from seal_core.chat.session import InMemorySessionStore
from seal_core.database.registry import DatabaseBundle, DatabaseRegistry
from seal_core.guardrails.models import ScopeResult
from tests.factory import build_client
from tests.mocks import MockIntrospector, MockPlanner
from tests.shared import AUTH_HEADERS


def _chat_service() -> ChatService:
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
    return ChatService(
        planner=MockPlanner(),
        registry=registry,
        sessions=InMemorySessionStore(),
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )


def test_chat_stream_refusal_seal_meta(monkeypatch) -> None:
    service = _chat_service()

    with (
        patch(
            "seal_core.chat.service.classify_scope",
            new=AsyncMock(
                return_value=ScopeResult(in_scope=False, reason="off-topic", source="heuristic")
            ),
        ),
        patch.object(
            service._client.chat.completions,
            "create",
            new=AsyncMock(
                return_value=ChatAnswer(
                    message="I can only help with your data.",
                    suggested_queries=["What tables are available?"],
                )
            ),
        ),
    ):
        client: TestClient = build_client(monkeypatch)
        client.app.dependency_overrides[get_chat_service] = lambda: service
        with client.stream(
            "POST",
            "/v1/chat",
            json={"message": "write a poem", "stream": True},
            headers=AUTH_HEADERS,
        ) as r:
            text = "".join(r.iter_text())

    assert r.status_code == 200
    assert "event: seal.meta" in text
    meta_line = next(
        line for line in text.splitlines() if line.startswith("data: {") and '"refusal"' in line
    )
    payload = json.loads(meta_line[6:])
    assert payload["refusal"] is True
    assert payload["used_sql"] is False
    assert payload["scope"]["in_scope"] is False
    assert payload["enhancement"]["enabled"] is False
    assert payload["sql"] is None
    assert payload["suggested_queries"] == ["What tables are available?"]
