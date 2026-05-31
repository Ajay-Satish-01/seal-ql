"""Postgres-backed workspace store (primary; seal_app.workspace_kv)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from seal_core.workspace.base import BaseWorkspaceStore
from seal_core.workspace.keys import CATALOG_OVERRIDES_KEY, WORKSPACE_SETTINGS_KEY

logger = logging.getLogger(__name__)

_POSTGRES_STORAGE_INFO = {
    "settings_read_source": "postgres",
    "catalog_read_source": "postgres",
    "write_target": "postgres",
}


class PostgresWorkspaceStore(BaseWorkspaceStore):
    """Persist workspace settings in seal_app.workspace_kv."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        self._pool: Any = None

    async def _pool_get(self) -> Any:
        if self._pool is None:
            import asyncpg

            self._pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=3)
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def ensure_schema(self) -> None:
        """Create seal_app.workspace_kv if missing (scripts/migrate_app.sql)."""
        migrate_path = Path(__file__).resolve().parents[4] / "scripts" / "migrate_app.sql"
        if not migrate_path.is_file():
            logger.warning("Workspace migration not found: %s", migrate_path)
            return
        pool = await self._pool_get()
        sql = migrate_path.read_text(encoding="utf-8")
        async with pool.acquire() as conn:
            await conn.execute(sql)
        logger.info("Applied workspace schema from %s", migrate_path)

    async def ping(self) -> bool:
        try:
            pool = await self._pool_get()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as exc:
            logger.warning("Postgres workspace store unavailable: %s", exc)
            return False

    async def _read_key(self, key: str) -> dict[str, Any]:
        pool = await self._pool_get()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value FROM seal_app.workspace_kv WHERE key = $1",
                key,
            )
        if row is None:
            return {}
        value = row["value"]
        if isinstance(value, str):
            return json.loads(value)
        return dict(value)

    async def _write_key(self, key: str, data: dict[str, Any]) -> None:
        pool = await self._pool_get()
        payload = json.dumps(data)
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO seal_app.workspace_kv (key, value, updated_at)
                VALUES ($1, $2::jsonb, NOW())
                ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value, updated_at = NOW()
                """,
                key,
                payload,
            )

    async def get_settings_blob(self) -> dict[str, Any]:
        return dict(await self._read_key(WORKSPACE_SETTINGS_KEY))

    async def save_settings_blob(self, data: dict[str, Any]) -> None:
        await self._write_key(WORKSPACE_SETTINGS_KEY, data)

    async def get_catalog_overrides(self) -> dict[str, Any]:
        return dict(await self._read_key(CATALOG_OVERRIDES_KEY))

    async def save_catalog_overrides(self, data: dict[str, Any]) -> None:
        await self._write_key(CATALOG_OVERRIDES_KEY, data)

    async def get_storage_info(self) -> dict[str, str]:
        return dict(_POSTGRES_STORAGE_INFO)
