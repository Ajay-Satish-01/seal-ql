"""Seal Python SDK — synchronous and async HTTP clients.

Usage (sync):
    from seal import Seal

    client = Seal("http://localhost:8000")
    result = client.query("Show me monthly revenue")
    print(result.sql)
    print(result.results)
    client.close()

Usage (async):
    from seal import AsyncSeal

    client = AsyncSeal("http://localhost:8000")
    result = await client.query("Show me monthly revenue")
    await client.close()

Usage (context manager):
    with Seal("http://localhost:8000") as client:
        result = client.query("Show me monthly revenue")

    async with AsyncSeal("http://localhost:8000") as client:
        result = await client.query("Show me monthly revenue")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

import httpx

from seal._sse import ChatStreamEvent, parse_sse_stream
from seal.exceptions import (
    QueryError,
    SealConnectionError,
    ServerError,
)
from seal.models import CatalogResponse, ChatResponse, DatabaseSchema, HealthResponse, QueryResponse

_DEFAULT_TIMEOUT = 120.0  # seconds — queries can be slow due to LLM


def _connection_error_message(base_url: str, exc: httpx.RequestError) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return f"Request to {base_url} timed out"
    return f"Cannot connect to {base_url}"


def _handle_error(response: httpx.Response) -> None:
    """Raise an appropriate SDK exception for non-2xx responses."""
    if response.status_code < 400:
        return

    try:
        detail = response.json().get("detail", response.text)
    except Exception:
        detail = response.text

    if response.status_code >= 500:
        raise ServerError(
            f"Server error ({response.status_code}): {detail}",
            status_code=response.status_code,
        )
    if response.status_code >= 400:
        raise QueryError(
            f"Query rejected ({response.status_code}): {detail}",
            status_code=response.status_code,
        )


# ============================================================
# Synchronous Client
# ============================================================


class Seal:
    """Synchronous client for the Seal API.

    Args:
        base_url: The base URL of the API server (e.g., "http://localhost:8000").
        api_key: Optional API key (sent as ``X-API-Key``).
        timeout: Request timeout in seconds (default: 120).
        headers: Optional extra headers to send with every request.
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        request_headers = dict(headers or {})
        if api_key:
            request_headers["X-API-Key"] = api_key
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
            headers=request_headers,
        )

    # -- Context manager --

    def __enter__(self) -> Seal:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    # -- Public API --

    def health(self) -> HealthResponse:
        """Check API health.

        Returns:
            HealthResponse with status information.

        Raises:
            SealConnectionError: If the API is unreachable.
        """
        try:
            resp = self._client.get("/health")
        except httpx.RequestError as exc:
            raise SealConnectionError(_connection_error_message(self._base_url, exc)) from exc

        _handle_error(resp)
        return HealthResponse.model_validate(resp.json())

    def query(self, query: str, *, database_id: str = "default") -> QueryResponse:
        """Send a natural language query to the API.

        Args:
            query: The natural language question.
            database_id: Optional database identifier.

        Returns:
            QueryResponse containing SQL, results, chart spec, and metadata.

        Raises:
            QueryError: If the API rejects the query (4xx).
            ServerError: If the API encounters an internal error (5xx).
            SealConnectionError: If the API is unreachable.
        """
        try:
            resp = self._client.post(
                "/v1/query",
                json={"query": query, "database_id": database_id},
            )
        except httpx.RequestError as exc:
            raise SealConnectionError(_connection_error_message(self._base_url, exc)) from exc

        _handle_error(resp)
        return QueryResponse.model_validate(resp.json())

    def schema(self) -> DatabaseSchema:
        """Fetch the introspected database schema.

        Returns:
            DatabaseSchema with all tables, columns, and metadata.

        Raises:
            SealConnectionError: If the API is unreachable.
        """
        try:
            resp = self._client.get("/v1/schema")
        except httpx.RequestError as exc:
            raise SealConnectionError(_connection_error_message(self._base_url, exc)) from exc

        _handle_error(resp)
        return DatabaseSchema.model_validate(resp.json())

    def catalog(self) -> CatalogResponse:
        """Fetch the global data catalog."""
        try:
            resp = self._client.get("/v1/catalog")
        except httpx.RequestError as exc:
            raise SealConnectionError(_connection_error_message(self._base_url, exc)) from exc
        _handle_error(resp)
        return CatalogResponse.model_validate(resp.json())

    def chat(
        self,
        message: str,
        *,
        session_id: str | None = None,
        include_charts: bool = False,
        stream: bool = False,
        enhancement: bool | None = None,
    ) -> ChatResponse:
        """Send a conversational message to /v1/chat."""
        if stream:
            raise ValueError("Use chat_stream() when stream=True")
        body: dict[str, Any] = {
            "message": message,
            "include_charts": include_charts,
            "stream": False,
        }
        if session_id:
            body["session_id"] = session_id
        if enhancement is not None:
            body["enhancement"] = enhancement
        try:
            resp = self._client.post("/v1/chat", json=body)
        except httpx.RequestError as exc:
            raise SealConnectionError(_connection_error_message(self._base_url, exc)) from exc
        _handle_error(resp)
        return ChatResponse.model_validate(resp.json())

    def chat_stream(
        self,
        message: str,
        *,
        session_id: str | None = None,
        include_charts: bool = False,
        enhancement: bool | None = None,
    ) -> Iterator[ChatStreamEvent]:
        """Stream chat answer events from /v1/chat (SSE)."""
        body: dict[str, Any] = {
            "message": message,
            "include_charts": include_charts,
            "stream": True,
        }
        if session_id:
            body["session_id"] = session_id
        if enhancement is not None:
            body["enhancement"] = enhancement
        try:
            with self._client.stream("POST", "/v1/chat", json=body) as resp:
                if resp.status_code >= 400:
                    resp.read()
                    _handle_error(resp)
                yield from parse_sse_stream(resp.iter_lines())
        except httpx.RequestError as exc:
            raise SealConnectionError(_connection_error_message(self._base_url, exc)) from exc


# ============================================================
# Async Client
# ============================================================


class AsyncSeal:
    """Async client for the Seal API.

    Args:
        base_url: The base URL of the API server (e.g., "http://localhost:8000").
        api_key: Optional API key (sent as ``X-API-Key``).
        timeout: Request timeout in seconds (default: 120).
        headers: Optional extra headers to send with every request.
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        request_headers = dict(headers or {})
        if api_key:
            request_headers["X-API-Key"] = api_key
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers=request_headers,
        )

    # -- Context manager --

    async def __aenter__(self) -> AsyncSeal:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    # -- Public API --

    async def health(self) -> HealthResponse:
        """Check API health.

        Returns:
            HealthResponse with status information.

        Raises:
            SealConnectionError: If the API is unreachable.
        """
        try:
            resp = await self._client.get("/health")
        except httpx.RequestError as exc:
            raise SealConnectionError(_connection_error_message(self._base_url, exc)) from exc

        _handle_error(resp)
        return HealthResponse.model_validate(resp.json())

    async def query(self, query: str, *, database_id: str = "default") -> QueryResponse:
        """Send a natural language query to the API.

        Args:
            query: The natural language question.
            database_id: Optional database identifier.

        Returns:
            QueryResponse containing SQL, results, chart spec, and metadata.

        Raises:
            QueryError: If the API rejects the query (4xx).
            ServerError: If the API encounters an internal error (5xx).
            SealConnectionError: If the API is unreachable.
        """
        try:
            resp = await self._client.post(
                "/v1/query",
                json={"query": query, "database_id": database_id},
            )
        except httpx.RequestError as exc:
            raise SealConnectionError(_connection_error_message(self._base_url, exc)) from exc

        _handle_error(resp)
        return QueryResponse.model_validate(resp.json())

    async def schema(self) -> DatabaseSchema:
        """Fetch the introspected database schema.

        Returns:
            DatabaseSchema with all tables, columns, and metadata.

        Raises:
            SealConnectionError: If the API is unreachable.
        """
        try:
            resp = await self._client.get("/v1/schema")
        except httpx.RequestError as exc:
            raise SealConnectionError(_connection_error_message(self._base_url, exc)) from exc

        _handle_error(resp)
        return DatabaseSchema.model_validate(resp.json())

    async def catalog(self) -> CatalogResponse:
        try:
            resp = await self._client.get("/v1/catalog")
        except httpx.RequestError as exc:
            raise SealConnectionError(_connection_error_message(self._base_url, exc)) from exc
        _handle_error(resp)
        return CatalogResponse.model_validate(resp.json())

    async def chat(
        self,
        message: str,
        *,
        session_id: str | None = None,
        include_charts: bool = False,
        enhancement: bool | None = None,
    ) -> ChatResponse:
        body: dict[str, Any] = {
            "message": message,
            "include_charts": include_charts,
            "stream": False,
        }
        if session_id:
            body["session_id"] = session_id
        if enhancement is not None:
            body["enhancement"] = enhancement
        try:
            resp = await self._client.post("/v1/chat", json=body)
        except httpx.RequestError as exc:
            raise SealConnectionError(_connection_error_message(self._base_url, exc)) from exc
        _handle_error(resp)
        return ChatResponse.model_validate(resp.json())

    async def chat_stream(
        self,
        message: str,
        *,
        session_id: str | None = None,
        include_charts: bool = False,
        enhancement: bool | None = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        """Stream chat answer events from /v1/chat (SSE)."""
        body: dict[str, Any] = {
            "message": message,
            "include_charts": include_charts,
            "stream": True,
        }
        if session_id:
            body["session_id"] = session_id
        if enhancement is not None:
            body["enhancement"] = enhancement
        try:
            async with self._client.stream("POST", "/v1/chat", json=body) as resp:
                if resp.status_code >= 400:
                    await resp.aread()
                    _handle_error(resp)
                buffer: list[str] = []
                async for line in resp.aiter_lines():
                    if line == "":
                        for event in parse_sse_stream(iter(buffer)):
                            yield event
                        buffer = []
                    else:
                        buffer.append(line)
                if buffer:
                    for event in parse_sse_stream(iter(buffer)):
                        yield event
        except httpx.RequestError as exc:
            raise SealConnectionError(_connection_error_message(self._base_url, exc)) from exc
