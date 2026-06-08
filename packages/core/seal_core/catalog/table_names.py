"""Helpers for resolving table names from catalog and schema."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from seal_core.catalog.registry import DataCatalogRegistry
    from seal_core.schema.models import DatabaseSchema


def catalog_table_names(registry: DataCatalogRegistry | Any | None) -> tuple[str, ...]:
    """Return lower-level table names from a loaded data catalog registry."""
    if registry is None:
        return ()
    catalog = getattr(registry, "catalog", None)
    entries = catalog.tables if catalog is not None else getattr(registry, "tables", None)
    if not entries:
        return ()
    return tuple(name for e in entries if (name := getattr(e, "name", "")).strip())


def schema_table_names_from_schema(schema: DatabaseSchema | Any | None) -> tuple[str, ...]:
    """Return table names from an introspected database schema."""
    if schema is None or not hasattr(schema, "tables"):
        return ()
    return tuple(t.name for t in schema.tables if hasattr(t, "name") and t.name.strip())


def merge_table_name_hints(*parts: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Dedupe table name hints preserving first-seen casing."""
    seen: dict[str, str] = {}
    for part in parts:
        for name in part:
            stripped = name.strip()
            if not stripped:
                continue
            key = stripped.lower()
            if key not in seen:
                seen[key] = stripped
    return tuple(seen.values())
