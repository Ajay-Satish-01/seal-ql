"""Unit tests for the Python SDK — mocked HTTP layer."""

from __future__ import annotations

import json

import httpx
import pytest
from intelligence_connector import (
    AsyncIntelligenceConnector,
    IntelligenceConnector,
    QueryError,
    ServerError,
)

# ============================================================
# Fixtures / Helpers
# ============================================================

_HEALTH_RESPONSE = {"status": "ok"}
_SCHEMA_RESPONSE = {"dialect": "postgres", "tables": []}
_QUERY_RESPONSE = {
    "sql": "SELECT 1 AS id LIMIT 10000",
    "columns": [{"name": "id", "type": "int", "nullable": True}],
    "results": [{"id": 1}],
    "chart": None,
    "metadata": {"row_count": 1},
}


def _mock_transport(
    status_code: int = 200,
    json_body: dict | None = None,
    text_body: str = "",
) -> httpx.MockTransport:
    """Create a mock transport that returns a fixed response."""

    def handler(request: httpx.Request) -> httpx.Response:
        if json_body is not None:
            return httpx.Response(
                status_code,
                content=json.dumps(json_body).encode(),
                headers={"content-type": "application/json"},
            )
        return httpx.Response(status_code, text=text_body)

    return handler


# ============================================================
# Sync Client Tests
# ============================================================


class TestSyncClient:
    """Tests for IntelligenceConnector (sync)."""

    def test_health(self):
        transport = httpx.MockTransport(_mock_transport(200, _HEALTH_RESPONSE))
        client = IntelligenceConnector.__new__(IntelligenceConnector)
        client._base_url = "http://testserver"
        client._client = httpx.Client(base_url="http://testserver", transport=transport)

        result = client.health()
        assert result.status == "ok"
        client.close()

    def test_query(self):
        transport = httpx.MockTransport(_mock_transport(200, _QUERY_RESPONSE))
        client = IntelligenceConnector.__new__(IntelligenceConnector)
        client._base_url = "http://testserver"
        client._client = httpx.Client(base_url="http://testserver", transport=transport)

        result = client.query("test query")
        assert result.sql == "SELECT 1 AS id LIMIT 10000"
        assert len(result.results) == 1
        assert result.results[0]["id"] == 1
        client.close()

    def test_schema(self):
        transport = httpx.MockTransport(_mock_transport(200, _SCHEMA_RESPONSE))
        client = IntelligenceConnector.__new__(IntelligenceConnector)
        client._base_url = "http://testserver"
        client._client = httpx.Client(base_url="http://testserver", transport=transport)

        result = client.schema()
        assert result.dialect == "postgres"
        assert result.tables == []
        client.close()

    def test_query_error_400(self):
        transport = httpx.MockTransport(_mock_transport(400, {"detail": "Validation failed"}))
        client = IntelligenceConnector.__new__(IntelligenceConnector)
        client._base_url = "http://testserver"
        client._client = httpx.Client(base_url="http://testserver", transport=transport)

        with pytest.raises(QueryError, match="Validation failed"):
            client.query("bad query")
        client.close()

    def test_server_error_500(self):
        transport = httpx.MockTransport(_mock_transport(500, {"detail": "Internal error"}))
        client = IntelligenceConnector.__new__(IntelligenceConnector)
        client._base_url = "http://testserver"
        client._client = httpx.Client(base_url="http://testserver", transport=transport)

        with pytest.raises(ServerError, match="Internal error"):
            client.query("query")
        client.close()

    def test_context_manager(self):
        transport = httpx.MockTransport(_mock_transport(200, _HEALTH_RESPONSE))
        with IntelligenceConnector.__new__(IntelligenceConnector) as client:
            client._base_url = "http://testserver"
            client._client = httpx.Client(base_url="http://testserver", transport=transport)
            result = client.health()
            assert result.status == "ok"


# ============================================================
# Async Client Tests
# ============================================================


class TestAsyncClient:
    """Tests for AsyncIntelligenceConnector."""

    @pytest.mark.asyncio
    async def test_health(self):
        transport = httpx.MockTransport(_mock_transport(200, _HEALTH_RESPONSE))
        client = AsyncIntelligenceConnector.__new__(AsyncIntelligenceConnector)
        client._base_url = "http://testserver"
        client._client = httpx.AsyncClient(base_url="http://testserver", transport=transport)

        result = await client.health()
        assert result.status == "ok"
        await client.close()

    @pytest.mark.asyncio
    async def test_query(self):
        transport = httpx.MockTransport(_mock_transport(200, _QUERY_RESPONSE))
        client = AsyncIntelligenceConnector.__new__(AsyncIntelligenceConnector)
        client._base_url = "http://testserver"
        client._client = httpx.AsyncClient(base_url="http://testserver", transport=transport)

        result = await client.query("test query")
        assert result.sql == "SELECT 1 AS id LIMIT 10000"
        assert len(result.results) == 1
        await client.close()

    @pytest.mark.asyncio
    async def test_query_error_400(self):
        transport = httpx.MockTransport(_mock_transport(400, {"detail": "Validation failed"}))
        client = AsyncIntelligenceConnector.__new__(AsyncIntelligenceConnector)
        client._base_url = "http://testserver"
        client._client = httpx.AsyncClient(base_url="http://testserver", transport=transport)

        with pytest.raises(QueryError, match="Validation failed"):
            await client.query("bad query")
        await client.close()

    @pytest.mark.asyncio
    async def test_server_error_500(self):
        transport = httpx.MockTransport(_mock_transport(500, {"detail": "Internal error"}))
        client = AsyncIntelligenceConnector.__new__(AsyncIntelligenceConnector)
        client._base_url = "http://testserver"
        client._client = httpx.AsyncClient(base_url="http://testserver", transport=transport)

        with pytest.raises(ServerError, match="Internal error"):
            await client.query("query")
        await client.close()


# ============================================================
# Model Tests
# ============================================================


class TestModels:
    """Verify models parse correctly from raw JSON."""

    def test_query_response_with_chart(self):
        from intelligence_connector.models import QueryResponse

        data = {
            "sql": "SELECT name FROM users LIMIT 5",
            "columns": [{"name": "name", "type": "text", "nullable": True}],
            "results": [{"name": "Alice"}, {"name": "Bob"}],
            "chart": {
                "chart_type": "bar",
                "vega_lite_spec": {"$schema": "https://vega.github.io/schema/vega-lite/v5.json"},
                "metadata": {},
            },
            "metadata": {"row_count": 2},
        }
        resp = QueryResponse.model_validate(data)
        assert resp.chart is not None
        assert resp.chart.chart_type.value == "bar"
        assert len(resp.results) == 2

    def test_query_response_no_chart(self):
        from intelligence_connector.models import QueryResponse

        data = {
            "sql": "SELECT 1",
            "columns": [{"name": "?column?", "type": "int"}],
            "results": [{"?column?": 1}],
            "chart": None,
            "metadata": {},
        }
        resp = QueryResponse.model_validate(data)
        assert resp.chart is None
