#!/usr/bin/env python3
"""Sync data catalog YAML from live database schema."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from seal_core.catalog.registry import DataCatalogRegistry
from seal_core.catalog.sync import sync_catalog
from seal_core.schema.introspector import get_introspector
from seal_core.settings import get_settings


async def main() -> int:
    settings = get_settings()
    if not settings.data_catalog_path:
        print("DATA_CATALOG_PATH is not set", file=sys.stderr)
        return 1

    dialect = "postgres" if "postgres" in settings.database_url else "duckdb"
    introspector = get_introspector(dialect, settings.database_url)
    try:
        schema = await introspector.introspect()
        path = Path(settings.data_catalog_path)
        result = await sync_catalog(schema, path, prune_removed=settings.catalog_prune_removed)
        registry = DataCatalogRegistry()
        registry.load(path)
        print(
            f"Synced {path}: added={result.added} updated={result.updated} removed={result.removed}"
        )
        return 0
    finally:
        await introspector.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
