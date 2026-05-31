"""Layered workspace store: Postgres primary, file fallback, env base."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from seal_core.workspace.file_store import FileWorkspaceStore
from seal_core.workspace.layered_store import LayeredWorkspaceStore
from seal_core.workspace.postgres_store import PostgresWorkspaceStore


@pytest.mark.asyncio
async def test_layered_reads_postgres_before_file(tmp_path: Path) -> None:
    primary = MagicMock(spec=PostgresWorkspaceStore)
    primary.ping = AsyncMock(return_value=True)
    primary.get_settings_blob = AsyncMock(return_value={"max_query_chars": 1000})
    primary.get_catalog_overrides = AsyncMock(return_value={})
    primary.close = AsyncMock()

    fallback = FileWorkspaceStore(path=tmp_path / "workspace.json")
    fallback_path = tmp_path / "workspace.json"
    fallback_path.write_text(
        json.dumps({"workspace_settings": {"max_query_chars": 2000}}),
        encoding="utf-8",
    )

    store = LayeredWorkspaceStore(primary, fallback)
    blob = await store.get_settings_blob()
    assert blob["max_query_chars"] == 1000
    info = await store.get_storage_info()
    assert info["settings_read_source"] == "postgres"


@pytest.mark.asyncio
async def test_layered_falls_back_to_file_when_db_empty(tmp_path: Path) -> None:
    primary = MagicMock(spec=PostgresWorkspaceStore)
    primary.ping = AsyncMock(return_value=True)
    primary.get_settings_blob = AsyncMock(return_value={})
    primary.get_catalog_overrides = AsyncMock(return_value={})
    primary.close = AsyncMock()

    fallback = FileWorkspaceStore(path=tmp_path / "workspace.json")
    (tmp_path / "workspace.json").write_text(
        json.dumps({"workspace_settings": {"guardrails_enabled": False}}),
        encoding="utf-8",
    )

    store = LayeredWorkspaceStore(primary, fallback)
    blob = await store.get_settings_blob()
    assert blob["guardrails_enabled"] is False
    info = await store.get_storage_info()
    assert info["settings_read_source"] == "file"


@pytest.mark.asyncio
async def test_layered_writes_to_postgres_when_available(tmp_path: Path) -> None:
    primary = MagicMock(spec=PostgresWorkspaceStore)
    primary.ping = AsyncMock(return_value=True)
    primary.get_settings_blob = AsyncMock(return_value={"max_query_chars": 1500})
    primary.get_catalog_overrides = AsyncMock(return_value={})
    primary.save_settings_blob = AsyncMock()
    primary.close = AsyncMock()

    fallback = FileWorkspaceStore(path=tmp_path / "workspace.json")
    store = LayeredWorkspaceStore(primary, fallback)
    await store.save_settings_blob({"max_query_chars": 1500})
    primary.save_settings_blob.assert_awaited_once()
    info = await store.get_storage_info()
    assert info["write_target"] == "postgres"
    assert not (tmp_path / "workspace.json").exists()


@pytest.mark.asyncio
async def test_layered_recovers_when_postgres_returns(tmp_path: Path) -> None:
    primary = MagicMock(spec=PostgresWorkspaceStore)
    primary.ping = AsyncMock(side_effect=[False, True])
    primary.get_settings_blob = AsyncMock(return_value={"max_query_chars": 1234})

    fallback = FileWorkspaceStore(path=tmp_path / "workspace.json")
    (tmp_path / "workspace.json").write_text(
        json.dumps({"workspace_settings": {"max_query_chars": 999}}),
        encoding="utf-8",
    )
    store = LayeredWorkspaceStore(primary, fallback)

    # First read: Postgres down -> file fallback.
    assert (await store.get_settings_blob())["max_query_chars"] == 999
    # Second read: negative ping is not cached, so Postgres is retried and wins.
    assert (await store.get_settings_blob())["max_query_chars"] == 1234
