"""End-to-end tests for the Python SDK against a live Docker stack.

These tests are skipped if the API server is not reachable.
Run `make up` before executing these tests.
"""

from __future__ import annotations

import os
import socket

import httpx
import pytest
from seal import (
    AsyncSeal,
    Seal,
)
from seal.exceptions import QueryError, SealError, ServerError
from tests.e2e_llm_helpers import (
    assert_chat_json_body,
    assert_query_json_body,
    probe_live_llm,
    skip_if_llm_unavailable,
)

_API_URL = "http://localhost:8000"
_API_KEY = os.environ.get("SEAL_API_KEY", "dev-local-change-me")


def _run_chat_e2e(client: Seal) -> None:
    try:
        result = client.chat("Name one table in the database.", stream=False)
    except (ServerError, SealError) as exc:
        skip_if_llm_unavailable(status_code=exc.status_code, body=str(exc), exc=exc)
        if isinstance(exc, QueryError):
            pytest.fail(f"Unexpected query-style error from chat: {exc}")
        raise
    except Exception as exc:
        skip_if_llm_unavailable(exc=exc)
        raise
    assert_chat_json_body(
        {
            "session_id": result.session_id,
            "message": result.message,
        }
    )


def _assert_query_result(result: object) -> None:
    from seal.models import QueryResponse

    assert isinstance(result, QueryResponse)
    assert_query_json_body(
        {
            "sql": result.sql,
            "results": result.results,
            "metadata": result.metadata,
        }
    )


def _handle_query_error(exc: QueryError) -> None:
    detail = str(exc).lower()
    if "out_of_scope" in detail or "query_out_of_scope" in detail:
        pytest.fail(f"Benign query incorrectly marked out of scope: {exc}")
    skip_if_llm_unavailable(status_code=exc.status_code, body=str(exc), exc=exc)
    pytest.fail(f"Unexpected query error: {exc}")


def _run_query_e2e(client: Seal) -> None:
    try:
        result = client.query("Show me 2 products")
    except QueryError as exc:
        _handle_query_error(exc)
    except (ServerError, SealError) as exc:
        skip_if_llm_unavailable(status_code=exc.status_code, body=str(exc), exc=exc)
        raise
    except Exception as exc:
        skip_if_llm_unavailable(exc=exc)
        raise
    else:
        _assert_query_result(result)


async def _run_query_e2e_async(client: AsyncSeal) -> None:
    try:
        result = await client.query("Show me 2 products")
    except QueryError as exc:
        _handle_query_error(exc)
    except (ServerError, SealError) as exc:
        skip_if_llm_unavailable(status_code=exc.status_code, body=str(exc), exc=exc)
        raise
    except Exception as exc:
        skip_if_llm_unavailable(exc=exc)
        raise
    else:
        _assert_query_result(result)


def _api_reachable() -> bool:
    """Check if the API server is reachable."""
    try:
        socket.create_connection(("localhost", 8000), timeout=2)
        return True
    except OSError:
        return False


@pytest.fixture(scope="module")
def llm_ready() -> None:
    """Skip LLM SDK tests when the live stack cannot complete a query."""
    reason = probe_live_llm(base_url=_API_URL, api_key=_API_KEY)
    if reason is not None:
        pytest.skip(f"LLM unavailable: {reason}")


@pytest.mark.skipif(
    not _api_reachable(),
    reason="API server not reachable at localhost:8000. Run 'make up' first.",
)
class TestSyncE2E:
    """E2E tests using the synchronous client."""

    def test_health(self):
        with Seal(_API_URL, api_key=_API_KEY) as client:
            result = client.health()
            assert result.status == "ok"

    def test_schema(self):
        with Seal(_API_URL, api_key=_API_KEY) as client:
            result = client.schema()
            assert result.dialect == "postgres"
            assert len(result.tables) > 0

    def test_catalog(self):
        with Seal(_API_URL, api_key=_API_KEY) as client:
            result = client.catalog()
            assert len(result.tables) > 0

    def test_catalog_descriptions_survive_sync(self):
        headers = {"X-API-Key": _API_KEY}
        with httpx.Client(base_url=_API_URL, headers=headers, timeout=60.0) as http:
            catalog = http.get("/v1/catalog")
            assert catalog.status_code == 200
            tables = catalog.json().get("tables", [])
            if not any(t.get("name") == "orders" for t in tables):
                pytest.skip("public.orders not in catalog (run make seed)")

            patch = http.patch(
                "/v1/catalog/descriptions",
                json={
                    "tables": [
                        {
                            "name": "orders",
                            "schema": "public",
                            "table_description": "SDK E2E override",
                        }
                    ]
                },
            )
            assert patch.status_code == 200, patch.text

            sync = http.post("/v1/catalog/sync")
            assert sync.status_code == 200, sync.text

            after = http.get("/v1/catalog")
            orders = next(t for t in after.json()["tables"] if t.get("name") == "orders")
            assert orders.get("table_description") == "SDK E2E override"

    def test_workspace_settings(self):
        headers = {"X-API-Key": _API_KEY}
        with httpx.Client(base_url=_API_URL, headers=headers, timeout=30.0) as http:
            r = http.get("/v1/workspace/settings")
            assert r.status_code == 200, r.text
            assert "settings" in r.json()

    def test_chat(self, llm_ready: None) -> None:
        with Seal(_API_URL, api_key=_API_KEY, timeout=180) as client:
            _run_chat_e2e(client)

    def test_query(self, llm_ready: None) -> None:
        with Seal(_API_URL, api_key=_API_KEY, timeout=180) as client:
            _run_query_e2e(client)


@pytest.mark.skipif(
    not _api_reachable(),
    reason="API server not reachable at localhost:8000. Run 'make up' first.",
)
class TestAsyncE2E:
    """E2E tests using the async client."""

    @pytest.mark.asyncio
    async def test_health(self):
        async with AsyncSeal(_API_URL, api_key=_API_KEY) as client:
            result = await client.health()
            assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_schema(self):
        async with AsyncSeal(_API_URL, api_key=_API_KEY) as client:
            result = await client.schema()
            assert result.dialect == "postgres"
            assert len(result.tables) > 0

    @pytest.mark.asyncio
    async def test_query(self, llm_ready: None) -> None:
        async with AsyncSeal(_API_URL, api_key=_API_KEY, timeout=180) as client:
            await _run_query_e2e_async(client)
