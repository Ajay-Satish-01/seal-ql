"""Tests for database_id routing on API routes."""

from __future__ import annotations

from app.dependencies import get_database_registry
from fastapi.testclient import TestClient
from seal_core.database.registry import DatabaseBundle
from tests.factory import build_client
from tests.mocks import (
    MockChatService,
    MockIntrospector,
    TrackingMockExecutor,
    make_mock_database_registry,
)
from tests.shared import AUTH_HEADERS


def test_unknown_database_id_on_query_returns_404(monkeypatch) -> None:
    client: TestClient = build_client(monkeypatch)
    response = client.post(
        "/v1/query",
        json={"query": "count orders", "database_id": "nonexistent"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "unknown_database_id"


def test_unknown_database_id_on_schema_returns_404(monkeypatch) -> None:
    client: TestClient = build_client(monkeypatch)
    response = client.get(
        "/v1/schema",
        params={"database_id": "nonexistent"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "unknown_database_id"


def test_unknown_database_id_on_chat_returns_404(monkeypatch) -> None:
    client: TestClient = build_client(monkeypatch)
    response = client.post(
        "/v1/chat",
        json={"message": "hello", "database_id": "nonexistent"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "unknown_database_id"


def test_unknown_database_id_on_query_before_scope_returns_404(monkeypatch) -> None:
    from unittest.mock import AsyncMock, patch

    from seal_core.guardrails.models import ScopeResult

    client: TestClient = build_client(monkeypatch)
    scope_mock = AsyncMock(
        return_value=ScopeResult(in_scope=False, reason="off-topic", source="heuristic")
    )
    with patch("app.routes.query.classify_scope", new=scope_mock):
        response = client.post(
            "/v1/query",
            json={"query": "write me a poem", "database_id": "nonexistent"},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 404
    assert response.json()["detail"] == "unknown_database_id"
    scope_mock.assert_not_called()


def test_empty_database_id_rejected_on_query(monkeypatch) -> None:
    client: TestClient = build_client(monkeypatch)
    response = client.post(
        "/v1/query",
        json={"query": "count orders", "database_id": ""},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 422


def test_empty_database_id_rejected_on_chat(monkeypatch) -> None:
    client: TestClient = build_client(monkeypatch)
    response = client.post(
        "/v1/chat",
        json={"message": "hello", "database_id": ""},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 422


def test_query_routes_to_named_database_executor(monkeypatch) -> None:
    analytics_executor = TrackingMockExecutor(database_id="analytics")
    analytics_bundle = DatabaseBundle(
        database_id="analytics",
        dialect="duckdb",
        url=":memory:",
        introspector=MockIntrospector(),
        executor=analytics_executor,
    )
    registry = make_mock_database_registry(extra={"analytics": analytics_bundle})

    client: TestClient = build_client(monkeypatch)
    client.app.dependency_overrides[get_database_registry] = lambda: registry

    response = client.post(
        "/v1/query",
        json={"query": "show orders", "database_id": "analytics"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    assert analytics_executor.calls
    assert response.json()["metadata"]["database_id"] == "analytics"


def test_chat_passes_database_id_to_service(monkeypatch) -> None:
    analytics_bundle = DatabaseBundle(
        database_id="analytics",
        dialect="duckdb",
        url=":memory:",
        introspector=MockIntrospector(),
        executor=TrackingMockExecutor(database_id="analytics"),
    )
    registry = make_mock_database_registry(extra={"analytics": analytics_bundle})

    MockChatService.last_database_id = None
    client: TestClient = build_client(monkeypatch)
    client.app.dependency_overrides[get_database_registry] = lambda: registry
    response = client.post(
        "/v1/chat",
        json={"message": "hello", "database_id": "analytics"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    assert MockChatService.last_database_id == "analytics"
    assert response.json()["metadata"]["database_id"] == "analytics"


def test_list_databases_returns_registry_ids(monkeypatch) -> None:
    analytics_bundle = DatabaseBundle(
        database_id="analytics",
        dialect="duckdb",
        url=":memory:",
        introspector=MockIntrospector(),
        executor=TrackingMockExecutor(database_id="analytics"),
    )
    registry = make_mock_database_registry(extra={"analytics": analytics_bundle})
    client: TestClient = build_client(monkeypatch)
    client.app.dependency_overrides[get_database_registry] = lambda: registry
    response = client.get("/v1/databases", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    ids = {item["database_id"] for item in body["databases"]}
    assert ids == {"analytics", "default"}
    default_row = next(d for d in body["databases"] if d["database_id"] == "default")
    assert default_row["is_default"] is True
