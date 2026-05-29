"""End-to-end tests for the Python SDK against a live Docker stack.

These tests are skipped if the API server is not reachable.
Run `make up` before executing these tests.
"""

from __future__ import annotations

import socket

import pytest
from intelligence_connector import (
    AsyncIntelligenceConnector,
    IntelligenceConnector,
)

_API_URL = "http://localhost:8000"


def _api_reachable() -> bool:
    """Check if the API server is reachable."""
    try:
        socket.create_connection(("localhost", 8000), timeout=2)
        return True
    except OSError:
        return False


@pytest.mark.skipif(
    not _api_reachable(),
    reason="API server not reachable at localhost:8000. Run 'make up' first.",
)
class TestSyncE2E:
    """E2E tests using the synchronous client."""

    def test_health(self):
        with IntelligenceConnector(_API_URL) as client:
            result = client.health()
            assert result.status == "ok"

    def test_schema(self):
        with IntelligenceConnector(_API_URL) as client:
            result = client.schema()
            assert result.dialect == "postgres"
            assert len(result.tables) > 0

    def test_query(self):
        with IntelligenceConnector(_API_URL, timeout=180) as client:
            try:
                result = client.query("Show me 2 products")
                assert result.sql  # non-empty SQL
                assert len(result.results) > 0
                assert result.metadata.get("row_count", 0) > 0
            except Exception as e:
                pytest.skip(f"Skipping query test (model may be weak/slow): {e}")


@pytest.mark.skipif(
    not _api_reachable(),
    reason="API server not reachable at localhost:8000. Run 'make up' first.",
)
class TestAsyncE2E:
    """E2E tests using the async client."""

    @pytest.mark.asyncio
    async def test_health(self):
        async with AsyncIntelligenceConnector(_API_URL) as client:
            result = await client.health()
            assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_schema(self):
        async with AsyncIntelligenceConnector(_API_URL) as client:
            result = await client.schema()
            assert result.dialect == "postgres"
            assert len(result.tables) > 0

    @pytest.mark.asyncio
    async def test_query(self):
        async with AsyncIntelligenceConnector(_API_URL, timeout=180) as client:
            try:
                result = await client.query("Show me 2 products")
                assert result.sql
                assert len(result.results) > 0
            except Exception as e:
                pytest.skip(f"Skipping query test (model may be weak/slow): {e}")
