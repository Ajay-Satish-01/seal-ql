"""DB-primary workspace store with file fallback and .env base defaults."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

from seal_core.workspace.base import BaseWorkspaceStore
from seal_core.workspace.keys import CATALOG_OVERRIDES_KEY, WORKSPACE_SETTINGS_KEY

if TYPE_CHECKING:
    from seal_core.workspace.file_store import FileWorkspaceStore
    from seal_core.workspace.postgres_store import PostgresWorkspaceStore

logger = logging.getLogger(__name__)

StorageSource = Literal["postgres", "file", "env"]


class LayeredWorkspaceStore(BaseWorkspaceStore):
    """Postgres is primary; config/workspace.json is read fallback; .env is the base layer."""

    def __init__(
        self,
        primary: PostgresWorkspaceStore,
        fallback: FileWorkspaceStore,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._postgres_ok: bool | None = None

    async def close(self) -> None:
        await self._primary.close()

    async def ensure_schema(self) -> None:
        # Best-effort: if Postgres is unreachable we degrade to the file
        # fallback instead of crashing startup.
        if not await self._postgres_usable():
            logger.warning(
                "Postgres unavailable at startup; using file fallback (%s)", self._fallback.path
            )
            return
        try:
            await self._primary.ensure_schema()
        except Exception as exc:  # noqa: BLE001 - never block boot on migration
            self._postgres_ok = None
            logger.warning("Could not apply workspace schema; using file fallback: %s", exc)

    async def _postgres_usable(self) -> bool:
        # Cache only the positive result; keep retrying while down so the store
        # recovers automatically once Postgres comes back.
        if self._postgres_ok:
            return True
        self._postgres_ok = await self._primary.ping()
        return self._postgres_ok

    async def _primary_blob(self, key: str) -> dict[str, Any]:
        if key == WORKSPACE_SETTINGS_KEY:
            return await self._primary.get_settings_blob()
        return await self._primary.get_catalog_overrides()

    async def _fallback_blob(self, key: str) -> dict[str, Any]:
        if key == WORKSPACE_SETTINGS_KEY:
            return await self._fallback.get_settings_blob()
        return await self._fallback.get_catalog_overrides()

    async def _resolve(self, key: str) -> tuple[dict[str, Any], StorageSource]:
        if await self._postgres_usable():
            primary_blob = await self._primary_blob(key)
            if primary_blob:
                return primary_blob, "postgres"

        fallback_blob = await self._fallback_blob(key)
        if fallback_blob:
            logger.info("Workspace %s loaded from file fallback (%s)", key, self._fallback.path)
            return fallback_blob, "file"

        return {}, "env"

    async def get_settings_blob(self) -> dict[str, Any]:
        blob, _ = await self._resolve(WORKSPACE_SETTINGS_KEY)
        return blob

    async def get_catalog_overrides(self) -> dict[str, Any]:
        blob, _ = await self._resolve(CATALOG_OVERRIDES_KEY)
        return blob

    async def _save(self, key: str, data: dict[str, Any]) -> None:
        target = self._primary if await self._postgres_usable() else self._fallback
        if key == WORKSPACE_SETTINGS_KEY:
            await target.save_settings_blob(data)
        else:
            await target.save_catalog_overrides(data)
        if target is self._fallback:
            logger.warning(
                "Postgres unavailable; workspace %s written to %s", key, self._fallback.path
            )

    async def save_settings_blob(self, data: dict[str, Any]) -> None:
        await self._save(WORKSPACE_SETTINGS_KEY, data)

    async def save_catalog_overrides(self, data: dict[str, Any]) -> None:
        await self._save(CATALOG_OVERRIDES_KEY, data)

    async def get_storage_info(self) -> dict[str, str]:
        # Computed fresh per call (no shared mutable state across requests).
        _, settings_src = await self._resolve(WORKSPACE_SETTINGS_KEY)
        _, catalog_src = await self._resolve(CATALOG_OVERRIDES_KEY)
        return {
            "settings_read_source": settings_src,
            "catalog_read_source": catalog_src,
            "write_target": "postgres" if await self._postgres_usable() else "file",
        }
