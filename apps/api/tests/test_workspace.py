"""API tests for workspace and catalog override routes."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.dependencies import get_workspace_store
from fastapi.testclient import TestClient
from seal_core.workspace.store import WorkspaceStore
from tests.factory import build_client
from tests.shared import AUTH_HEADERS


@pytest.fixture
def workspace_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    store = WorkspaceStore(path=tmp_path / "workspace.json")
    client = build_client(monkeypatch, SEAL_DEV_MODE="true")
    client.app.dependency_overrides[get_workspace_store] = lambda: store
    client.app.state.workspace_store = store
    return client


def test_get_workspace_settings(workspace_client: TestClient) -> None:
    r = workspace_client.get("/v1/workspace/settings", headers=AUTH_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "settings" in body
    assert "schema" in body
    keys = {f["key"] for f in body["schema"]}
    assert "guardrails_enabled" in keys


def test_patch_workspace_prod_persists_without_hot_reload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from seal_core.settings import clear_settings_cache, get_settings

    store = WorkspaceStore(path=tmp_path / "workspace.json")
    client = build_client(monkeypatch, SEAL_DEV_MODE="false")
    client.app.dependency_overrides[get_workspace_store] = lambda: store
    before = get_settings().max_query_chars
    r = client.patch(
        "/v1/workspace/settings",
        json={"settings": {"max_query_chars": 3000}},
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["settings"]["max_query_chars"] == 3000
    assert body["hot_reload_applied"] == []
    assert "max_query_chars" in body["pending_apply"]
    assert get_settings().max_query_chars == before

    apply_r = client.post("/v1/workspace/settings/apply", headers=AUTH_HEADERS)
    assert apply_r.status_code == 200
    assert "max_query_chars" in apply_r.json()["hot_reload_applied"]
    assert get_settings().max_query_chars == 3000
    clear_settings_cache()


def test_patch_workspace_settings_hot_reload(workspace_client: TestClient) -> None:
    r = workspace_client.patch(
        "/v1/workspace/settings",
        json={"settings": {"guardrails_enabled": False}},
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["settings"]["guardrails_enabled"] is False
    assert "guardrails_enabled" in body["hot_reload_applied"]
    assert body["pending_apply"] == []


def test_patch_workspace_restart_required_keys(workspace_client: TestClient) -> None:
    r = workspace_client.patch(
        "/v1/workspace/settings",
        json={"settings": {"vector_store": "chroma"}},
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 200
    assert "vector_store" in r.json().get("restart_required", [])


def test_patch_catalog_descriptions(workspace_client: TestClient, tmp_path: Path) -> None:
    import json

    from seal_core.workspace.keys import CATALOG_OVERRIDES_KEY

    r = workspace_client.patch(
        "/v1/catalog/descriptions",
        json={
            "tables": [
                {
                    "name": "orders",
                    "schema": "public",
                    "table_description": "Customer orders",
                }
            ]
        },
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert "tables" in body
    orders = next((t for t in body["tables"] if t.get("name") == "orders"), None)
    if orders is not None:
        assert orders.get("table_description") == "Customer orders"

    blob = json.loads((tmp_path / "workspace.json").read_text(encoding="utf-8"))
    assert blob[CATALOG_OVERRIDES_KEY]["public.orders"]["table_description"] == "Customer orders"
