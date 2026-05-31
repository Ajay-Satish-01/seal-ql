"""Postgres workspace store catalog override round-trip (skips without Postgres)."""

from __future__ import annotations

import pytest
from seal_core.settings import get_settings
from seal_core.workspace.postgres_store import PostgresWorkspaceStore


def _store() -> PostgresWorkspaceStore | None:
    settings = get_settings()
    if "postgres" not in settings.database_url.lower():
        return None
    url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    return PostgresWorkspaceStore(url)


@pytest.mark.asyncio
async def test_postgres_catalog_overrides_roundtrip() -> None:
    store = _store()
    if store is None:
        pytest.skip("DATABASE_URL is not Postgres")

    try:
        await store.ensure_schema()
        if not await store.ping():
            pytest.skip("Postgres is not reachable")
    except Exception as exc:
        pytest.skip(f"Postgres unavailable: {exc}")

    await store.save_catalog_overrides({})
    try:
        await store.save_catalog_overrides(
            {
                "public.orders": {"table_description": "Persisted in workspace_kv"},
            }
        )
        loaded = await store.get_catalog_overrides()
        assert loaded["public.orders"]["table_description"] == "Persisted in workspace_kv"
    finally:
        await store.save_catalog_overrides({})
        await store.close()
