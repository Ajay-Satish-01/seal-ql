from app.dependencies import get_chat_service, get_database_registry
from fastapi.testclient import TestClient
from seal_core.chat.errors import SessionDatabaseMismatchError
from seal_core.database.registry import DatabaseBundle
from tests.factory import build_client
from tests.mocks import (
    MockChatService,
    MockIntrospector,
    TrackingMockExecutor,
    make_mock_database_registry,
)
from tests.shared import AUTH_HEADERS


def test_chat_stream_sse(monkeypatch) -> None:
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
    with client.stream(
        "POST",
        "/v1/chat",
        json={"message": "Hi", "stream": True, "database_id": "analytics"},
        headers=AUTH_HEADERS,
    ) as r:
        assert r.status_code == 200
        text = "".join(r.iter_text())
    assert "seal.meta" in text
    compact = text.replace(" ", "")
    assert '"database_id":"analytics"' in compact
    assert '"repair_attempts":' in compact
    assert '"row_count":' in compact
    assert '"enhancement":' in compact
    assert MockChatService.last_database_id == "analytics"
    assert "[DONE]" in text


def test_chat_stream_session_database_mismatch_returns_400(monkeypatch) -> None:
    class MismatchChatService:
        async def prepare_stream_turn(self, **kwargs):
            raise SessionDatabaseMismatchError(
                session_id="s1",
                pinned_database_id="default",
                requested_database_id="analytics",
            )

        async def stream_turn(self, *args, **kwargs):
            if False:
                yield ""

    client: TestClient = build_client(monkeypatch)
    client.app.dependency_overrides[get_chat_service] = lambda: MismatchChatService()
    analytics_bundle = DatabaseBundle(
        database_id="analytics",
        dialect="duckdb",
        url=":memory:",
        introspector=MockIntrospector(),
        executor=TrackingMockExecutor(database_id="analytics"),
    )
    registry = make_mock_database_registry(extra={"analytics": analytics_bundle})
    client.app.dependency_overrides[get_database_registry] = lambda: registry

    response = client.post(
        "/v1/chat",
        json={"message": "Hi", "stream": True, "session_id": "s1", "database_id": "analytics"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "session_database_id_mismatch"
