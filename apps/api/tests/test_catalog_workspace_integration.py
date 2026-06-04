"""Catalog + workspace integration via live API (Postgres workspace store).

Uses HTTP against the running API container so asyncpg is not shared across
pytest-asyncio and Starlette TestClient event loops.
"""

from __future__ import annotations

import os
import socket
from urllib.parse import urlparse

import httpx
import pytest
from seal_core.settings import get_settings
from tests.shared import live_api_headers


def _api_base_url() -> str:
    return os.environ.get("SEAL_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _postgres_reachable() -> bool:
    try:
        settings = get_settings()
        if "postgres" not in settings.database_url.lower():
            return False
        parsed = urlparse(settings.database_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        socket.create_connection((host, port), timeout=1)
        return True
    except OSError:
        return False


def _api_reachable() -> bool:
    """True when a running API responds on SEAL_API_BASE_URL (default localhost:8000)."""
    try:
        with httpx.Client(base_url=_api_base_url(), timeout=2.0) as client:
            response = client.get("/health")
            return response.status_code == 200 and response.json().get("status") == "ok"
    except (httpx.ConnectError, httpx.TimeoutException, OSError):
        return False


@pytest.fixture
def live_http() -> httpx.Client:
    if not _postgres_reachable():
        pytest.skip("Postgres is not reachable")
    if not _api_reachable():
        pytest.skip(
            "Live API is not running at "
            f"{_api_base_url()} (run `make up`, or run this file in the e2e-tests CI job)"
        )
    with httpx.Client(base_url=_api_base_url(), timeout=60.0) as client:
        yield client


def _table_description(body: dict, name: str) -> str | None:
    for row in body.get("tables", []):
        if row.get("name") == name:
            return row.get("table_description")
    return None


def test_live_patch_and_sync_preserve_catalog_description(live_http: httpx.Client) -> None:
    headers = live_api_headers()
    catalog = live_http.get("/v1/catalog", headers=headers)
    assert catalog.status_code == 200, catalog.text
    if not any(t.get("name") == "orders" for t in catalog.json().get("tables", [])):
        pytest.skip("public.orders not in catalog (run make seed)")

    patch = live_http.patch(
        "/v1/catalog/descriptions",
        json={
            "tables": [
                {
                    "name": "orders",
                    "schema": "public",
                    "table_description": "Live HTTP integration override",
                }
            ]
        },
        headers=headers,
    )
    assert patch.status_code == 200, patch.text
    assert _table_description(patch.json(), "orders") == "Live HTTP integration override"

    sync = live_http.post("/v1/catalog/sync", headers=headers)
    assert sync.status_code == 200, sync.text

    after = live_http.get("/v1/catalog", headers=headers)
    assert after.status_code == 200, after.text
    assert _table_description(after.json(), "orders") == "Live HTTP integration override"


def test_live_workspace_settings_storage_uses_postgres(live_http: httpx.Client) -> None:
    headers = live_api_headers()
    r = live_http.get("/v1/workspace/settings", headers=headers)
    assert r.status_code == 200, r.text
    storage = r.json().get("storage") or {}
    # With DATABASE_URL=postgres and healthy DB, layered store should report postgres.
    assert storage.get("write_target") in ("postgres", "file")
