"""Shared workspace store logic.

Subclasses provide blob persistence (``get_*_blob`` / ``save_*``); the merge,
hot-reload, and export semantics live here so every backend behaves identically.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from seal_core.workspace.settings_merge import (
    apply_persisted_hot_reload,
    build_patch_result,
    effective_settings_for_api,
    prepare_apply_persisted,
    prepare_settings_patch,
)

_FILE_STORAGE_INFO = {
    "settings_read_source": "file",
    "catalog_read_source": "file",
    "write_target": "file",
}


class BaseWorkspaceStore(ABC):
    """Backend-agnostic settings/catalog override store."""

    @abstractmethod
    async def get_settings_blob(self) -> dict[str, Any]:
        """Return persisted settings overrides (empty dict when none)."""

    @abstractmethod
    async def save_settings_blob(self, data: dict[str, Any]) -> None:
        """Persist settings overrides."""

    @abstractmethod
    async def get_catalog_overrides(self) -> dict[str, Any]:
        """Return persisted catalog description overrides (empty dict when none)."""

    @abstractmethod
    async def save_catalog_overrides(self, data: dict[str, Any]) -> None:
        """Persist catalog description overrides."""

    async def close(self) -> None:
        return None

    async def get_storage_info(self) -> dict[str, str]:
        """Report read/write provenance for the dashboard (overridable)."""
        return dict(_FILE_STORAGE_INFO)

    async def load_effective_settings(self) -> dict[str, Any]:
        return effective_settings_for_api(await self.get_settings_blob())

    async def patch_settings(
        self, patch: dict[str, Any], *, apply_hot_reload: bool = False
    ) -> dict[str, Any]:
        stored = await self.get_settings_blob()
        persisted, merged, hot_keys, restart_keys = prepare_settings_patch(stored, patch)
        await self.save_settings_blob(persisted)
        result = build_patch_result(
            merged, hot_keys, restart_keys, apply_hot_reload_now=apply_hot_reload
        )
        result["storage"] = await self.get_storage_info()
        return result

    async def apply_persisted_settings(self) -> dict[str, Any]:
        stored = await self.get_settings_blob()
        merged, hot_keys, restart_keys = prepare_apply_persisted(stored)
        result = apply_persisted_hot_reload(merged, hot_keys)
        result["restart_required"] = restart_keys
        result["storage"] = await self.get_storage_info()
        return result

    async def export_all(self) -> dict[str, Any]:
        return {
            "settings": await self.load_effective_settings(),
            "catalog_overrides": await self.get_catalog_overrides(),
        }
