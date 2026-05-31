"""Tests for workspace settings merge and file store."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from seal_core.settings import clear_settings_cache
from seal_core.workspace import settings_merge as sm
from seal_core.workspace.settings_merge import merge_workspace_patch, prepare_settings_patch
from seal_core.workspace.settings_schema import schema_by_key
from seal_core.workspace.store import WorkspaceStore


def test_merge_workspace_patch_unknown_key() -> None:
    with pytest.raises(ValueError, match="Unknown settings"):
        merge_workspace_patch({"not_a_setting": True})


def test_merge_workspace_patch_bool_validation() -> None:
    with pytest.raises(ValueError, match="boolean"):
        merge_workspace_patch({"guardrails_enabled": "yes"})


def test_merge_workspace_patch_hot_vs_restart() -> None:
    merged, hot, restart = merge_workspace_patch({"guardrails_enabled": False})
    assert merged["guardrails_enabled"] is False
    assert "guardrails_enabled" in hot
    assert "vector_store" not in hot


@pytest.mark.asyncio
async def test_workspace_store_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "workspace.json"
    store = WorkspaceStore(path=path)

    result = await store.patch_settings({"max_query_chars": 2000})
    assert result["settings"]["max_query_chars"] == 2000

    blob = json.loads(path.read_text(encoding="utf-8"))
    assert blob["workspace_settings"]["max_query_chars"] == 2000

    effective = await store.load_effective_settings()
    assert effective["max_query_chars"] == 2000


@pytest.mark.asyncio
async def test_patch_persists_only_diffs_from_env(tmp_path: Path) -> None:
    """Only values that differ from the .env base are snapshotted to storage."""
    clear_settings_cache()  # isolate from sibling tests that mutate the singleton
    path = tmp_path / "workspace.json"
    store = WorkspaceStore(path=path)

    await store.patch_settings({"max_query_chars": 2000})
    blob = json.loads(path.read_text(encoding="utf-8"))["workspace_settings"]
    assert blob == {"max_query_chars": 2000}  # not a full snapshot of every key

    # Reverting to the .env default (4000) removes the override entirely.
    await store.patch_settings({"max_query_chars": 4000})
    blob = json.loads(path.read_text(encoding="utf-8"))["workspace_settings"]
    assert "max_query_chars" not in blob


def test_prepare_settings_patch_drops_masked_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """A masked sentinel echoed back from GET must never overwrite the real value."""
    clear_settings_cache()  # isolate from sibling tests that mutate the singleton
    fields = dict(schema_by_key())
    fields["llm_model"] = replace(fields["llm_model"], secret=True)
    monkeypatch.setattr(sm, "schema_by_key", lambda: fields)

    persisted, _merged, _hot, _restart = prepare_settings_patch(
        {}, {"llm_model": "***", "max_query_chars": 2000}
    )
    assert "llm_model" not in persisted
    assert persisted["max_query_chars"] == 2000
