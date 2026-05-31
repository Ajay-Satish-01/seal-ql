"""Shared fixtures for catalog + workspace integration tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from seal_core.catalog.registry import DataCatalogRegistry
from seal_core.catalog.sync import sync_catalog
from seal_core.schema.models import ColumnInfo, ColumnType, DatabaseSchema, TableKind, TableSchema
from seal_core.settings import get_settings
from seal_core.workspace.keys import CATALOG_OVERRIDES_KEY
from seal_core.workspace.postgres_store import PostgresWorkspaceStore

if TYPE_CHECKING:
    from seal_core.workspace.store import WorkspaceStore


def orders_table() -> TableSchema:
    return TableSchema(
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
            ),
            ColumnInfo(
                name="amount",
                data_type="numeric",
                normalized_type=ColumnType.NUMERIC,
                nullable=False,
                is_primary_key=False,
            ),
        ],
    )


class OrdersIntrospector:
    """Returns a minimal schema with public.orders for catalog sync tests."""

    async def introspect(self) -> DatabaseSchema:
        return DatabaseSchema(dialect="postgres", tables=[orders_table()])


async def seed_catalog_yaml(path: Path) -> DataCatalogRegistry:
    """Write catalog.yaml from introspection and return a loaded registry."""
    schema = DatabaseSchema(dialect="postgres", tables=[orders_table()])
    await sync_catalog(schema, path)
    registry = DataCatalogRegistry()
    registry.load(path)
    return registry


def _postgres_store_from_settings() -> PostgresWorkspaceStore | None:
    settings = get_settings()
    if "postgres" not in settings.database_url.lower():
        return None
    url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    return PostgresWorkspaceStore(url)


async def postgres_workspace_available() -> bool:
    store = _postgres_store_from_settings()
    if store is None:
        return False
    try:
        await store.ensure_schema()
        ok = await store.ping()
        await store.close()
        return ok
    except Exception:
        return False


def run_async(coro):  # noqa: ANN001
    return asyncio.run(coro)


@pytest.fixture
def postgres_workspace_store() -> WorkspaceStore:
    """Real Postgres workspace store (skips when DB is unavailable).

    Setup/teardown use HTTP in integration tests where possible to avoid mixing
    asyncio.run() with FastAPI TestClient's event loop on the same asyncpg pool.
    """
    if not run_async(postgres_workspace_available()):
        pytest.skip("Postgres workspace store is not available")

    store = _postgres_store_from_settings()
    assert store is not None
    yield store


def table_description(body: dict, name: str, schema: str = "public") -> str | None:
    for row in body.get("tables", []):
        if row.get("name") == name and (row.get("schema") or "public") == schema:
            return row.get("table_description")
    return None


def assert_kv_has_description(store: WorkspaceStore, description: str) -> None:
    overrides = run_async(store.get_catalog_overrides())
    entry = overrides.get("public.orders", {})
    assert entry.get("table_description") == description


# Re-export key for tests that assert raw persistence
__all__ = [
    "CATALOG_OVERRIDES_KEY",
    "OrdersIntrospector",
    "orders_table",
    "postgres_workspace_available",
    "postgres_workspace_store",
    "run_async",
    "seed_catalog_yaml",
    "table_description",
    "assert_kv_has_description",
]
