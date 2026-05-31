"""Workspace store factory (Postgres primary, file fallback, .env base)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from seal_core.settings import get_settings
from seal_core.workspace.file_store import FileWorkspaceStore
from seal_core.workspace.layered_store import LayeredWorkspaceStore
from seal_core.workspace.postgres_store import PostgresWorkspaceStore

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# Backward-compatible alias for tests and imports.
WorkspaceStore = FileWorkspaceStore


def create_workspace_store(
    path: str | Path | None = None,
) -> LayeredWorkspaceStore | FileWorkspaceStore:
    """Create the workspace store for this process.

    - Default: Postgres ``seal_app.workspace_kv`` (dashboard writes go here).
    - Read fallback: ``config/workspace.json`` when DB has no row yet.
    - Effective values: stored overrides merged on top of ``.env`` / environment.
    - Set ``WORKSPACE_STORE=file`` to force file-only (tests, offline).
    """
    settings = get_settings()
    fallback = FileWorkspaceStore(path=path)

    if settings.workspace_store.lower() == "file":
        logger.info("Workspace store: file only (%s)", fallback.path)
        return fallback

    if "postgres" not in settings.database_url.lower():
        logger.info(
            "Workspace store: file only (non-Postgres DATABASE_URL): %s",
            fallback.path,
        )
        return fallback

    primary = PostgresWorkspaceStore(settings.database_url)
    logger.info("Workspace store: postgres primary with file fallback (%s)", fallback.path)
    return LayeredWorkspaceStore(primary, fallback)
