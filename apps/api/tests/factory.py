"""Test client factory for API tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.dependencies import (
    get_chat_service,
    get_data_catalog,
    get_query_executor,
    get_query_planner,
    get_schema_introspector,
    get_semantic_registry,
)
from app.main import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient
from seal_core.settings import Settings, clear_settings_cache
from tests.mocks import (
    MockChatService,
    MockDataCatalog,
    MockExecutor,
    MockIntrospector,
    MockPlanner,
    MockSemanticRegistry,
)

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


def apply_dependency_mocks(application: FastAPI) -> None:
    """Attach in-memory mocks so /v1/* tests do not require Postgres."""
    application.dependency_overrides[get_schema_introspector] = lambda: MockIntrospector()
    application.dependency_overrides[get_query_planner] = lambda: MockPlanner()
    application.dependency_overrides[get_query_executor] = lambda: MockExecutor()
    application.dependency_overrides[get_semantic_registry] = lambda: MockSemanticRegistry()
    application.dependency_overrides[get_data_catalog] = lambda: MockDataCatalog()
    application.dependency_overrides[get_chat_service] = lambda: MockChatService()


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
