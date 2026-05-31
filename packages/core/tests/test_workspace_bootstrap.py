"""Tests for workspace startup bootstrap helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from seal_core.catalog.registry import DataCatalogRegistry
from seal_core.catalog.sync import sync_catalog
from seal_core.schema.models import ColumnInfo, ColumnType, DatabaseSchema, TableKind, TableSchema
from seal_core.workspace.bootstrap import apply_workspace_on_startup
from seal_core.workspace.store import WorkspaceStore


@pytest.mark.asyncio
async def test_apply_workspace_on_startup_applies_settings(tmp_path: Path) -> None:
    store = WorkspaceStore(path=tmp_path / "workspace.json")
    await store.patch_settings({"max_query_chars": 1500}, apply_hot_reload=False)
    registry = DataCatalogRegistry()

    await apply_workspace_on_startup(store, registry)

    from seal_core.settings import get_settings

    assert get_settings().max_query_chars == 1500


@pytest.mark.asyncio
async def test_apply_workspace_on_startup_applies_catalog_overrides(tmp_path: Path) -> None:
    store = WorkspaceStore(path=tmp_path / "workspace.json")
    await store.save_catalog_overrides(
        {"public.orders": {"table_description": "Bootstrap override"}}
    )
    registry = DataCatalogRegistry()
    catalog_path = tmp_path / "catalog.yaml"
    table = TableSchema(
        name="orders",
        schema_name="public",
        kind=TableKind.TABLE,
        columns=[
            ColumnInfo(
                name="id",
                data_type="integer",
                normalized_type=ColumnType.INTEGER,
                nullable=False,
                is_primary_key=True,
            )
        ],
    )
    await sync_catalog(DatabaseSchema(dialect="postgres", tables=[table]), catalog_path)
    registry.load(catalog_path)

    await apply_workspace_on_startup(store, registry)

    entry = registry.get_entry("orders", "public")
    assert entry is not None
    assert entry.table_description == "Bootstrap override"
