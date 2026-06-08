"""Shared pytest configuration for API tests."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from app.main import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient
from seal_core.settings import Settings, clear_settings_cache
from tests.factory import apply_dependency_mocks, clear_dependency_mocks
from tests.shared import TEST_API_KEY


@pytest.fixture(autouse=True)
def _configure_test_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Use a consistent API key and clear settings cache between tests."""
    # Do not load the developer's .env during tests (would leak SEAL_API_KEY, LLM keys, etc.)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    monkeypatch.setenv("SEAL_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("SEAL_DEV_MODE", "true")
    monkeypatch.setenv("SEAL_DISABLE_DOCS", "false")
    monkeypatch.setenv("VECTOR_STORE", "none")
    monkeypatch.setenv("CATALOG_AUTO_SYNC", "false")
    monkeypatch.setenv("CHAT_ENHANCEMENT_ENABLED", "false")
    monkeypatch.setenv("CHAT_SESSION_STORE", "memory")
    monkeypatch.delenv("CHAT_SESSION_DATABASE_URL", raising=False)
    monkeypatch.setenv("GUARDRAILS_ENABLED", "false")
    monkeypatch.setenv("SEAL_TRUST_EXPLAINABILITY_ENABLED", "false")
    monkeypatch.setenv("SEAL_DATABASES_PATH", "/nonexistent/seal-databases.yaml")
    clear_settings_cache()
    yield
    clear_settings_cache()


@pytest.fixture
def api_app() -> Generator[FastAPI, None, None]:
    """Fresh FastAPI app with mocked DB/LLM dependencies (no global mutation)."""
    clear_settings_cache()
    application = create_app()
    apply_dependency_mocks(application)
    yield application
    clear_dependency_mocks(application)
    clear_settings_cache()


@pytest.fixture
def api_client(api_app: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(api_app) as client:
        yield client
