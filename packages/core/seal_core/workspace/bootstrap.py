"""Apply persisted workspace settings and catalog overrides at API startup."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from seal_core.workspace.settings_merge import (
    apply_hot_reload,
    prepare_apply_persisted,
)

if TYPE_CHECKING:
    from seal_core.catalog.registry import DataCatalogRegistry
    from seal_core.workspace.store import WorkspaceStore

logger = logging.getLogger(__name__)


def apply_catalog_overrides_to_registry(
    registry: DataCatalogRegistry,
    overrides: dict[str, Any],
) -> None:
    """Merge stored description overrides into the in-memory catalog registry."""
    for key, payload in overrides.items():
        if not isinstance(payload, dict):
            continue
        parts = key.split(".", 1)
        if len(parts) != 2:
            logger.warning("Skipping catalog override key (expected schema.table): %s", key)
            continue
        schema_name, name = parts
        entry = registry.get_entry(name, schema_name)
        if entry is None:
            continue
        if payload.get("table_description") is not None:
            entry.table_description = payload["table_description"]
        if payload.get("view_description") is not None:
            entry.view_description = payload["view_description"]


async def apply_workspace_on_startup(
    store: WorkspaceStore,
    registry: DataCatalogRegistry,
) -> None:
    """Load workspace.json settings and catalog overrides into the running process."""
    stored = await store.get_settings_blob()
    if stored:
        merged, hot_keys, restart_keys = prepare_apply_persisted(stored)
        keys = hot_keys + restart_keys
        if keys:
            apply_hot_reload(merged, keys)
            logger.info("Applied workspace settings on startup: %s", ", ".join(keys))

    overrides = await store.get_catalog_overrides()
    if overrides:
        apply_catalog_overrides_to_registry(registry, overrides)
        logger.info("Applied %d catalog description override(s) on startup", len(overrides))
