"""Shared fixtures for live HTTP E2E tests against a running API."""

from __future__ import annotations

import os
import socket
from collections.abc import Generator
from urllib.parse import urlparse

import httpx
import pytest
from seal_core.settings import get_settings
from tests.shared import live_api_headers


def api_base_url() -> str:
    return os.environ.get("SEAL_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def postgres_reachable() -> bool:
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


def api_reachable() -> bool:
    try:
        with httpx.Client(base_url=api_base_url(), timeout=2.0) as client:
            response = client.get("/health")
            return response.status_code == 200 and response.json().get("status") == "ok"
    except (httpx.ConnectError, httpx.TimeoutException, OSError):
        return False


def catalog_table_names(client: httpx.Client, headers: dict[str, str]) -> list[str]:
    response = client.get("/v1/catalog", headers=headers)
    if response.status_code != 200:
        return []
    tables = response.json().get("tables", [])
    return [str(t["name"]) for t in tables if isinstance(t, dict) and t.get("name")]


@pytest.fixture
def live_http() -> Generator[httpx.Client, None, None]:
    if not postgres_reachable():
        pytest.skip("Postgres is not reachable")
    if not api_reachable():
        pytest.skip(
            "Live API is not running at "
            f"{api_base_url()} (run `make up`, or run this file in the e2e-tests CI job)"
        )
    with httpx.Client(base_url=api_base_url(), timeout=60.0) as client:
        yield client


@pytest.fixture
def live_http_llm(live_http: httpx.Client) -> httpx.Client:
    """Live HTTP client with a longer timeout for LLM-backed routes."""
    live_http.timeout = httpx.Timeout(180.0)
    return live_http


@pytest.fixture
def catalog_table_name(live_http: httpx.Client) -> str:
    names = catalog_table_names(live_http, live_api_headers())
    if not names:
        pytest.skip("Catalog has no tables (run make seed)")
    return names[0]
