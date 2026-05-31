"""Dedicated tests for file-backed WorkspaceStore."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from seal_core.workspace.store import WorkspaceStore


@pytest.mark.asyncio
async def test_workspace_store_file_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "workspace.json"
    store = WorkspaceStore(path=path)

    result = await store.patch_settings({"guardrails_enabled": False}, apply_hot_reload=True)
    assert result["settings"]["guardrails_enabled"] is False
    assert "guardrails_enabled" in result["hot_reload_applied"]
    assert result["pending_apply"] == []

    blob = json.loads(path.read_text(encoding="utf-8"))
    assert blob["workspace_settings"]["guardrails_enabled"] is False

    overrides = {"public.orders": {"table_description": "Orders"}}
    await store.save_catalog_overrides(overrides)
    loaded = await store.get_catalog_overrides()
    assert loaded["public.orders"]["table_description"] == "Orders"
