"""Tests for disabling public OpenAPI / Swagger routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.main import create_app
from fastapi.testclient import TestClient
from seal_core.settings import get_settings
from tests.shared import TEST_API_KEY

if TYPE_CHECKING:
    import pytest


def test_public_docs_disabled_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEAL_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("SEAL_DISABLE_DOCS", "true")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404

    get_settings.cache_clear()


def test_public_docs_enabled_by_default_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEAL_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("SEAL_AUTH_REQUIRED", "false")
    monkeypatch.setenv("SEAL_DISABLE_DOCS", "false")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200

    get_settings.cache_clear()
