"""Catalog HTTP routes with file-backed workspace (no Postgres required)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.dependencies import get_data_catalog, get_schema_introspector, get_workspace_store
from fastapi.testclient import TestClient
from seal_core.workspace.keys import CATALOG_OVERRIDES_KEY
from seal_core.workspace.store import WorkspaceStore
from tests.catalog_fixtures import (
    OrdersIntrospector,
    assert_kv_has_description,
    run_async,
    seed_catalog_yaml,
    table_description,
)
from tests.factory import build_client
from tests.shared import AUTH_HEADERS


@pytest.fixture
def catalog_file_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    catalog_path = tmp_path / "catalog.yaml"
    workspace_path = tmp_path / "workspace.json"
    registry = run_async(seed_catalog_yaml(catalog_path))
    store = WorkspaceStore(path=workspace_path)

    monkeypatch.setenv("DATA_CATALOG_PATH", str(catalog_path))
    client = build_client(monkeypatch, mock_dependencies=True)
    client.app.dependency_overrides[get_workspace_store] = lambda: store
    client.app.dependency_overrides[get_data_catalog] = lambda: registry
    client.app.dependency_overrides[get_schema_introspector] = lambda: OrdersIntrospector()
    client.app.state.workspace_store = store
    client.app.state.data_catalog = registry
    return client


def test_catalog_sync_writes_yaml(catalog_file_client: TestClient, tmp_path: Path) -> None:
    r = catalog_file_client.post("/v1/catalog/sync", headers=AUTH_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["path"]
    assert body["added"] >= 0


def test_patch_descriptions_persist_to_workspace_file(catalog_file_client: TestClient) -> None:
    store = catalog_file_client.app.state.workspace_store
    r = catalog_file_client.patch(
        "/v1/catalog/descriptions",
        json={
            "tables": [
                {
                    "name": "orders",
                    "schema": "public",
                    "table_description": "Customer orders (test)",
                }
            ]
        },
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 200
    assert table_description(r.json(), "orders") == "Customer orders (test)"
    assert_kv_has_description(store, "Customer orders (test)")


def test_sync_reapplies_descriptions_from_workspace_file(catalog_file_client: TestClient) -> None:
    store = catalog_file_client.app.state.workspace_store
    catalog_file_client.patch(
        "/v1/catalog/descriptions",
        json={
            "tables": [
                {
                    "name": "orders",
                    "schema": "public",
                    "table_description": "Survives YAML regen",
                }
            ]
        },
        headers=AUTH_HEADERS,
    )
    assert_kv_has_description(store, "Survives YAML regen")

    sync_r = catalog_file_client.post("/v1/catalog/sync", headers=AUTH_HEADERS)
    assert sync_r.status_code == 200

    get_r = catalog_file_client.get("/v1/catalog", headers=AUTH_HEADERS)
    assert get_r.status_code == 200
    assert table_description(get_r.json(), "orders") == "Survives YAML regen"


def test_patch_descriptions_merge_without_wiping_other_fields(
    catalog_file_client: TestClient, tmp_path: Path
) -> None:
    catalog_file_client.patch(
        "/v1/catalog/descriptions",
        json={
            "tables": [
                {
                    "name": "orders",
                    "schema": "public",
                    "table_description": "Table text",
                    "view_description": "View text",
                }
            ]
        },
        headers=AUTH_HEADERS,
    )
    catalog_file_client.patch(
        "/v1/catalog/descriptions",
        json={
            "tables": [
                {
                    "name": "orders",
                    "schema": "public",
                    "table_description": "Table text updated",
                }
            ]
        },
        headers=AUTH_HEADERS,
    )
    blob = json.loads((tmp_path / "workspace.json").read_text(encoding="utf-8"))
    entry = blob[CATALOG_OVERRIDES_KEY]["public.orders"]
    assert entry["table_description"] == "Table text updated"
    assert entry["view_description"] == "View text"


def test_workspace_json_has_catalog_overrides_key(
    catalog_file_client: TestClient, tmp_path: Path
) -> None:
    catalog_file_client.patch(
        "/v1/catalog/descriptions",
        json={"tables": [{"name": "orders", "schema": "public", "table_description": "On disk"}]},
        headers=AUTH_HEADERS,
    )
    blob = json.loads((tmp_path / "workspace.json").read_text(encoding="utf-8"))
    assert CATALOG_OVERRIDES_KEY in blob
    assert blob[CATALOG_OVERRIDES_KEY]["public.orders"]["table_description"] == "On disk"
