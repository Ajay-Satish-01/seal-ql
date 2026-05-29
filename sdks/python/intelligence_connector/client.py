"""Intelligence Connector Python SDK — synchronous and async HTTP clients.

Usage (sync):
    from intelligence_connector import IntelligenceConnector

    client = IntelligenceConnector("http://localhost:8000")
    result = client.query("Show me monthly revenue")
    print(result.sql)
    print(result.results)
    client.close()

Usage (async):
    from intelligence_connector import AsyncIntelligenceConnector

    client = AsyncIntelligenceConnector("http://localhost:8000")
    result = await client.query("Show me monthly revenue")
    await client.close()

Usage (context manager):
    with IntelligenceConnector("http://localhost:8000") as client:
        result = client.query("Show me monthly revenue")

    async with AsyncIntelligenceConnector("http://localhost:8000") as client:
        result = await client.query("Show me monthly revenue")
"""

from __future__ import annotations

from typing import Any

import httpx

from intelligence_connector.exceptions import (
    ConnectionError,
    QueryError,
    ServerError,
)
from intelligence_connector.models import DatabaseSchema, HealthResponse, QueryResponse

_DEFAULT_TIMEOUT = 120.0  # seconds — queries can be slow due to LLM


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


class IntelligenceConnector:
    """Synchronous client for the Intelligence Connector API.

    Args:
        base_url: The base URL of the API server (e.g., "http://localhost:8000").
        timeout: Request timeout in seconds (default: 120).
        headers: Optional extra headers to send with every request.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
            headers=headers or {},
        )

    # -- Context manager --

    def __enter__(self) -> IntelligenceConnector:
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
            ConnectionError: If the API is unreachable.
        """
        try:
            resp = self._client.get("/health")
        except httpx.ConnectError as exc:
            raise ConnectionError(f"Cannot connect to {self._base_url}") from exc

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
            ConnectionError: If the API is unreachable.
        """
        try:
            resp = self._client.post(
                "/v1/query",
                json={"query": query, "database_id": database_id},
            )
        except httpx.ConnectError as exc:
            raise ConnectionError(f"Cannot connect to {self._base_url}") from exc

        _handle_error(resp)
        return QueryResponse.model_validate(resp.json())

    def schema(self) -> DatabaseSchema:
        """Fetch the introspected database schema.

        Returns:
            DatabaseSchema with all tables, columns, and metadata.

        Raises:
            ConnectionError: If the API is unreachable.
        """
        try:
            resp = self._client.get("/v1/schema")
        except httpx.ConnectError as exc:
            raise ConnectionError(f"Cannot connect to {self._base_url}") from exc

        _handle_error(resp)
        return DatabaseSchema.model_validate(resp.json())


# ============================================================
# Async Client
# ============================================================


class AsyncIntelligenceConnector:
    """Async client for the Intelligence Connector API.

    Args:
        base_url: The base URL of the API server (e.g., "http://localhost:8000").
        timeout: Request timeout in seconds (default: 120).
        headers: Optional extra headers to send with every request.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers=headers or {},
        )

    # -- Context manager --

    async def __aenter__(self) -> AsyncIntelligenceConnector:
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
            ConnectionError: If the API is unreachable.
        """
        try:
            resp = await self._client.get("/health")
        except httpx.ConnectError as exc:
            raise ConnectionError(f"Cannot connect to {self._base_url}") from exc

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
            ConnectionError: If the API is unreachable.
        """
        try:
            resp = await self._client.post(
                "/v1/query",
                json={"query": query, "database_id": database_id},
            )
        except httpx.ConnectError as exc:
            raise ConnectionError(f"Cannot connect to {self._base_url}") from exc

        _handle_error(resp)
        return QueryResponse.model_validate(resp.json())

    async def schema(self) -> DatabaseSchema:
        """Fetch the introspected database schema.

        Returns:
            DatabaseSchema with all tables, columns, and metadata.

        Raises:
            ConnectionError: If the API is unreachable.
        """
        try:
            resp = await self._client.get("/v1/schema")
        except httpx.ConnectError as exc:
            raise ConnectionError(f"Cannot connect to {self._base_url}") from exc

        _handle_error(resp)
        return DatabaseSchema.model_validate(resp.json())
