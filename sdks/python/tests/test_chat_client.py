"""SDK tests for catalog and chat endpoints."""

from __future__ import annotations

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
