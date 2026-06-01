"""SDK tests for catalog and chat endpoints."""

from __future__ import annotations

import json

import httpx
import pytest
from seal import Seal
from seal._sse import parse_sse_stream

_CHAT_RESPONSE = {
    "session_id": "s1",
    "message": "Hello",
    "sources": [],
    "metadata": {},
}

_CATALOG_RESPONSE = {
    "version": 1,
    "tables": [],
}


def _mock_transport(routes: dict[str, tuple[int, dict | str]]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.method} {request.url.path}"
        if key not in routes:
            return httpx.Response(404, text="not found")
        status, body = routes[key]
        if isinstance(body, dict):
            return httpx.Response(status, json=body)
        return httpx.Response(status, text=body, headers={"content-type": "text/event-stream"})

    return httpx.MockTransport(handler)


class TestChatClient:
    def test_catalog(self) -> None:
        transport = _mock_transport({"GET /v1/catalog": (200, _CATALOG_RESPONSE)})
        client = Seal.__new__(Seal)
        client._base_url = "http://testserver"
        client._client = httpx.Client(base_url="http://testserver", transport=transport)
        result = client.catalog()
        assert result.version == 1
        client.close()

    def test_chat(self) -> None:
        transport = _mock_transport({"POST /v1/chat": (200, _CHAT_RESPONSE)})
        client = Seal.__new__(Seal)
        client._base_url = "http://testserver"
        client._client = httpx.Client(base_url="http://testserver", transport=transport)
        result = client.chat("Hi")
        assert result.message == "Hello"
        client.close()

    def test_chat_parses_execution_metadata(self) -> None:
        body = {
            "session_id": "s1",
            "message": "ok",
            "sql": "SELECT 1",
            "columns": [{"name": "n", "type": "int"}],
            "metadata": {
                "database_id": "default",
                "row_count": 1,
                "execution_time_ms": 1.0,
                "truncated": False,
                "warnings": [],
                "repair_attempts": 0,
                "used_sql": True,
                "enhancement": {"enabled": False, "applied": []},
            },
        }
        transport = _mock_transport({"POST /v1/chat": (200, body)})
        client = Seal.__new__(Seal)
        client._base_url = "http://testserver"
        client._client = httpx.Client(base_url="http://testserver", transport=transport)
        resp = client.chat("count")
        assert resp.metadata.row_count == 1  # type: ignore[union-attr]
        assert resp.metadata.repair_attempts == 0  # type: ignore[union-attr]
        assert resp.metadata.enhancement.enabled is False  # type: ignore[union-attr]
        client.close()

    def test_chat_sends_database_id(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=_CHAT_RESPONSE)

        transport = httpx.MockTransport(handler)
        client = Seal.__new__(Seal)
        client._base_url = "http://testserver"
        client._client = httpx.Client(base_url="http://testserver", transport=transport)
        client.chat("Hi", database_id="analytics")
        assert captured["body"] == {
            "message": "Hi",
            "include_charts": False,
            "stream": False,
            "database_id": "analytics",
        }
        client.close()

    def test_parse_sse(self) -> None:
        lines = [
            "event: seal.meta",
            'data: {"session_id":"s1"}',
            "",
            'data: {"choices":[{"delta":{"content":"Hi"}}]}',
            "",
            "data: [DONE]",
            "",
        ]
        events = list(parse_sse_stream(iter(lines)))
        assert events[0]["type"] == "meta"
        assert events[1]["type"] == "delta"
        assert events[2]["type"] == "done"

    def test_parse_sse_meta_error_on_invalid_json(self) -> None:
        lines = ["event: seal.meta", "data: {not-json", ""]
        events = list(parse_sse_stream(iter(lines)))
        assert events[0]["type"] == "meta_error"
        assert "error" in events[0]

    def test_parse_sse_meta_error_on_validation_failure(self) -> None:
        lines = [
            "event: seal.meta",
            'data: {"session_id":"s1","sql":"SELECT 1","used_sql":true}',
            "",
        ]
        events = list(parse_sse_stream(iter(lines)))
        assert events[0]["type"] == "meta_error"
        assert events[0]["partial"]["session_id"] == "s1"


@pytest.mark.asyncio
async def test_async_chat_stream() -> None:
    sse = (
        'event: seal.meta\ndata: {"session_id":"s1"}\n\n'
        'data: {"choices":[{"delta":{"content":"x"}}]}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})

    transport = httpx.MockTransport(handler)
    from seal import AsyncSeal

    client = AsyncSeal.__new__(AsyncSeal)
    client._base_url = "http://testserver"
    client._client = httpx.AsyncClient(base_url="http://testserver", transport=transport)

    collected = []
    async for event in client.chat_stream("Hi"):
        collected.append(event)
    await client.close()
    assert collected[0]["type"] == "meta"
    assert collected[-1]["type"] == "done"
