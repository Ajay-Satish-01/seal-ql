"""Live end-to-end tests against the Docker stack (no dependency mocks)."""

from __future__ import annotations

import os
import socket
from collections.abc import Generator
from urllib.parse import urlparse

import pytest
from app.main import app
from fastapi.testclient import TestClient
from seal_core.settings import get_settings
from tests.e2e_llm_helpers import (
    assert_chat_json_body,
    assert_query_json_body,
    skip_if_llm_unavailable,
)
from tests.shared import TEST_API_KEY


def is_docker_running() -> bool:
    """Check if we can connect to the target database via Settings."""
    try:
        settings = get_settings()
        parsed = urlparse(settings.database_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        socket.create_connection((host, port), timeout=1)
        return True
    except OSError:
        return False


def api_headers() -> dict[str, str]:
    return {"X-API-Key": os.environ.get("SEAL_API_KEY", TEST_API_KEY)}


@pytest.fixture
def live_client() -> Generator[TestClient, None, None]:
    if not is_docker_running():
        pytest.skip("Docker stack is not running. Please run 'make up'.")
    # Do not re-raise 5xx from LLM/provider errors; tests skip vs fail explicitly below.
    with TestClient(app, raise_server_exceptions=False) as client:
        health = client.get("/health")
        if health.status_code != 200:
            pytest.skip(f"API health check failed: {health.text}")
        yield client


def test_e2e_health(live_client: TestClient) -> None:
    r = live_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_e2e_get_catalog(live_client: TestClient) -> None:
    r = live_client.get("/v1/catalog", headers=api_headers())
    assert r.status_code != 401, r.text
    assert r.status_code == 200
    assert isinstance(r.json().get("tables"), list)


def test_e2e_workspace_settings(live_client: TestClient) -> None:
    r = live_client.get("/v1/workspace/settings", headers=api_headers())
    assert r.status_code != 401, r.text
    assert r.status_code == 200
    body = r.json()
    assert "settings" in body
    assert "schema" in body


def test_e2e_catalog_descriptions_survive_sync(live_client: TestClient) -> None:
    """PATCH description → Postgres/file store → POST sync → GET catalog keeps text."""
    headers = api_headers()
    catalog = live_client.get("/v1/catalog", headers=headers)
    assert catalog.status_code == 200
    tables = catalog.json().get("tables", [])
    if not any(t.get("name") == "orders" for t in tables):
        pytest.skip("Seed data table public.orders not in catalog")

    patch = live_client.patch(
        "/v1/catalog/descriptions",
        json={
            "tables": [
                {
                    "name": "orders",
                    "schema": "public",
                    "table_description": "E2E catalog override",
                }
            ]
        },
        headers=headers,
    )
    assert patch.status_code == 200, patch.text

    sync = live_client.post("/v1/catalog/sync", headers=headers)
    assert sync.status_code == 200, sync.text

    after = live_client.get("/v1/catalog", headers=headers)
    assert after.status_code == 200
    orders = next(t for t in after.json()["tables"] if t.get("name") == "orders")
    assert orders.get("table_description") == "E2E catalog override"


def test_e2e_chat_json(live_client: TestClient) -> None:
    headers = api_headers()
    try:
        r = live_client.post(
            "/v1/chat",
            json={
                "message": "List one table name only.",
                "include_charts": False,
                "stream": False,
            },
            headers=headers,
        )
    except Exception as exc:
        skip_if_llm_unavailable(exc=exc)
        raise

    assert r.status_code != 401, r.text
    skip_if_llm_unavailable(status_code=r.status_code, body=r.text)
    if r.status_code == 400:
        pytest.fail(f"Unexpected 400 from chat on benign prompt: {r.text}")
    assert r.status_code == 200, r.text
    assert_chat_json_body(r.json())


def test_e2e_live_query(live_client: TestClient) -> None:
    """Natural language query against seeded products table."""
    headers = api_headers()
    try:
        response = live_client.post(
            "/v1/query",
            json={"query": "Show me 2 products"},
            headers=headers,
        )
    except Exception as exc:
        skip_if_llm_unavailable(exc=exc)
        raise

    assert response.status_code != 401, f"Unexpected 401 (auth regression): {response.text}"
    skip_if_llm_unavailable(status_code=response.status_code, body=response.text)
    detail = ""
    try:
        detail = str(response.json().get("detail", ""))
    except Exception:
        detail = response.text
    if response.status_code == 400 and "out_of_scope" in detail:
        pytest.fail(f"Benign query incorrectly marked out of scope: {response.text}")
    if response.status_code == 400:
        pytest.fail(f"Unexpected 400 from query: {response.text}")
    assert response.status_code == 200, response.text
    assert_query_json_body(response.json())
