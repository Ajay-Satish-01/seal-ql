from fastapi.testclient import TestClient
from tests.factory import build_client
from tests.shared import AUTH_HEADERS


def test_chat_stream_sse(monkeypatch) -> None:
    client: TestClient = build_client(monkeypatch)
    with client.stream(
        "POST",
        "/v1/chat",
        json={"message": "Hi", "stream": True},
        headers=AUTH_HEADERS,
    ) as r:
        assert r.status_code == 200
        text = "".join(r.iter_text())
    assert "seal.meta" in text
    assert "[DONE]" in text
