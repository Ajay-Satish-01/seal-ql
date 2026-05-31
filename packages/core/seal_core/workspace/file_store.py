"""File-backed workspace store (fallback when Postgres is empty or unavailable)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from seal_core.settings import get_settings
from seal_core.workspace.base import BaseWorkspaceStore
from seal_core.workspace.keys import CATALOG_OVERRIDES_KEY, WORKSPACE_SETTINGS_KEY

logger = logging.getLogger(__name__)


def default_workspace_json_path() -> Path:
    settings = get_settings()
    catalog_parent = Path(settings.data_catalog_path or "config/catalog.yaml").parent
    return catalog_parent / "workspace.json"


class FileWorkspaceStore(BaseWorkspaceStore):
    """Read/write workspace settings and catalog overrides in config/workspace.json."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path else default_workspace_json_path()

    @property
    def path(self) -> Path:
        return self._path

    def _read_blob(self) -> dict[str, Any]:
        if not self._path.is_file():
            return {}
        with open(self._path, encoding="utf-8") as f:
            return json.load(f)

    def _write_blob(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    async def get_settings_blob(self) -> dict[str, Any]:
        return dict(self._read_blob().get(WORKSPACE_SETTINGS_KEY, {}))

    async def save_settings_blob(self, data: dict[str, Any]) -> None:
        blob = self._read_blob()
        blob[WORKSPACE_SETTINGS_KEY] = data
        self._write_blob(blob)

    async def get_catalog_overrides(self) -> dict[str, Any]:
        return dict(self._read_blob().get(CATALOG_OVERRIDES_KEY, {}))

    async def save_catalog_overrides(self, data: dict[str, Any]) -> None:
        blob = self._read_blob()
        blob[CATALOG_OVERRIDES_KEY] = data
        self._write_blob(blob)

    async def get_storage_info(self) -> dict[str, str]:
        blob = self._read_blob()
        return {
            "settings_read_source": "file" if blob.get(WORKSPACE_SETTINGS_KEY) else "env",
            "catalog_read_source": "file" if blob.get(CATALOG_OVERRIDES_KEY) else "env",
            "write_target": "file",
        }
