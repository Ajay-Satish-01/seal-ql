from fastapi.testclient import TestClient
from tests.factory import build_client
from tests.shared import AUTH_HEADERS


def test_chat_json_response(monkeypatch) -> None:
    client: TestClient = build_client(monkeypatch)
    r = client.post(
        "/v1/chat",
        json={"message": "What tables exist?", "include_charts": False},
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert "session_id" in body
    assert "message" in body


def test_chat_with_database_id(monkeypatch) -> None:
    from tests.mocks import MockChatService

    MockChatService.last_database_id = None
    client: TestClient = build_client(monkeypatch)
    r = client.post(
        "/v1/chat",
        json={"message": "Hi", "database_id": "default"},
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 200
    assert MockChatService.last_database_id == "default"


def test_chat_session_persistence(monkeypatch) -> None:
    client: TestClient = build_client(monkeypatch)
    r1 = client.post("/v1/chat", json={"message": "Hello"}, headers=AUTH_HEADERS)
    sid = r1.json()["session_id"]
    r2 = client.post(
        "/v1/chat",
        json={"message": "Follow up", "session_id": sid},
        headers=AUTH_HEADERS,
    )
    assert r2.status_code == 200
    assert r2.json()["session_id"] == sid


def test_get_catalog(monkeypatch) -> None:
    client: TestClient = build_client(monkeypatch)
    r = client.get("/v1/catalog", headers=AUTH_HEADERS)
    assert r.status_code == 200
    assert "tables" in r.json()


def test_query_out_of_scope_returns_400(monkeypatch) -> None:
    from unittest.mock import AsyncMock, patch

    from seal_core.guardrails.models import ScopeResult

    client: TestClient = build_client(monkeypatch)
    with patch(
        "app.routes.query.classify_scope",
        new=AsyncMock(
            return_value=ScopeResult(in_scope=False, reason="off-topic", source="heuristic")
        ),
    ):
        r = client.post(
            "/v1/query",
            json={"query": "write me a poem"},
            headers=AUTH_HEADERS,
        )
    assert r.status_code == 400
    assert r.json()["detail"] == "query_out_of_scope"
