"""Test client factory for API tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.dependencies import (
    get_chat_service,
    get_data_catalog,
    get_database_registry,
    get_query_planner,
    get_reasoning_orchestrator,
    get_semantic_registry,
)
from app.main import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient
from seal_core.reasoning.orchestrator import build_default_orchestrator
from seal_core.settings import Settings, clear_settings_cache
from tests.mocks import (
    MockChatService,
    MockDataCatalog,
    MockPlanner,
    MockSemanticRegistry,
    make_mock_database_registry,
)

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


def apply_dependency_mocks(application: FastAPI) -> None:
    """Attach in-memory mocks so /v1/* tests do not require Postgres."""
    registry = make_mock_database_registry()
    reasoning = build_default_orchestrator()
    planner = MockPlanner()
    catalog = MockDataCatalog()
    semantic = MockSemanticRegistry()
    application.dependency_overrides[get_database_registry] = lambda: registry
    application.dependency_overrides[get_query_planner] = lambda: planner
    application.dependency_overrides[get_semantic_registry] = lambda: semantic
    application.dependency_overrides[get_data_catalog] = lambda: catalog
    application.dependency_overrides[get_chat_service] = lambda: MockChatService()
    application.dependency_overrides[get_reasoning_orchestrator] = lambda: reasoning


def clear_dependency_mocks(application: FastAPI) -> None:
    application.dependency_overrides.clear()


def build_client(
    monkeypatch: MonkeyPatch,
    *,
    mock_dependencies: bool = True,
    **env: str | None,
) -> TestClient:
    """Build a TestClient after env overrides; optionally attach route mocks."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    clear_settings_cache()
    application = create_app()
    if mock_dependencies:
        apply_dependency_mocks(application)
    return TestClient(application)
