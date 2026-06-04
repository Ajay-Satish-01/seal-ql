"""Merge-safe sync of catalog YAML from database introspection."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING

import yaml

from seal_core.catalog.models import (
    CatalogEntry,
    CatalogSyncResult,
    DataCatalog,
    catalog_entry_key,
    utc_now_iso,
)
from seal_core.catalog.registry import entry_from_table
from seal_core.schema.models import DatabaseSchema, TableKind, TableSchema

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

_TABLE_KINDS = {TableKind.TABLE, TableKind.HYPERTABLE}
_VIEW_KINDS = {TableKind.VIEW, TableKind.MATERIALIZED_VIEW, TableKind.CONTINUOUS_AGGREGATE}

# Application metadata (chat sessions, workspace KV) — not NL-queryable analytics tables.
_EXCLUDED_CATALOG_SCHEMAS = frozenset({"seal_app"})


def _is_catalog_eligible(table: TableSchema) -> bool:
    return table.schema_name not in _EXCLUDED_CATALOG_SCHEMAS


def _eligible_tables(schema: DatabaseSchema) -> list[TableSchema]:
    return [t for t in schema.tables if _is_catalog_eligible(t)]


def _structural_hash(schema: DatabaseSchema) -> str:
    payload = [
        {
            "schema": t.schema_name,
            "name": t.name,
            "kind": t.kind.value,
            "columns": [(c.name, c.data_type) for c in t.columns],
        }
        for t in _eligible_tables(schema)
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def _merge_descriptions(
    existing: CatalogEntry,
    new_kind: TableKind,
) -> tuple[str | None, str | None]:
    table_desc = existing.table_description
    view_desc = existing.view_description

    if existing.kind in _VIEW_KINDS and new_kind in _TABLE_KINDS:
        if table_desc is None and view_desc:
            table_desc = view_desc
            view_desc = None
            logger.info("Migrated view_description to table_description for %s", existing.name)
    elif (
        existing.kind in _TABLE_KINDS
        and new_kind in _VIEW_KINDS
        and view_desc is None
        and table_desc
    ):
        view_desc = table_desc
        table_desc = None
        logger.info("Migrated table_description to view_description for %s", existing.name)

    return table_desc, view_desc


def _entry_from_table_merge(existing: CatalogEntry | None, table: TableSchema) -> CatalogEntry:
    fresh = entry_from_table(table)
    if existing is None:
        return fresh

    table_desc, view_desc = _merge_descriptions(existing, table.kind)
    if table_desc is None and view_desc is None and table.description:
        if table.kind in _VIEW_KINDS:
            view_desc = table.description
        else:
            table_desc = table.description

    # Only fall back to the previously stored description when the kind is
    # unchanged. After a kind flip, _merge_descriptions has already migrated (or
    # intentionally cleared) the fields, so reusing existing.*_description would
    # resurrect stale metadata on the opposite slot.
    same_kind = table.kind == existing.kind
    return CatalogEntry(
        schema=table.schema_name,
        name=table.name,
        kind=table.kind,
        columns=fresh.columns,
        table_description=(
            table_desc if table_desc is not None or not same_kind else existing.table_description
        ),
        view_description=(
            view_desc if view_desc is not None or not same_kind else existing.view_description
        ),
    )


async def sync_catalog(
    schema: DatabaseSchema,
    catalog_path: Path,
    *,
    prune_removed: bool = True,
) -> CatalogSyncResult:
    """Sync catalog YAML from introspected schema, preserving user descriptions."""
    catalog_path.parent.mkdir(parents=True, exist_ok=True)

    existing_map: dict[tuple[str, str], CatalogEntry] = {}
    if catalog_path.is_file():
        with open(catalog_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        if raw:
            catalog = DataCatalog.model_validate(raw)
            for entry in catalog.tables:
                existing_map[catalog_entry_key(entry.schema_name, entry.name)] = entry

    result = CatalogSyncResult(path=str(catalog_path))
    new_tables: list[CatalogEntry] = []
    seen_keys: set[tuple[str, str]] = set()

    for table in _eligible_tables(schema):
        key = catalog_entry_key(table.schema_name, table.name)
        seen_keys.add(key)
        prev = existing_map.get(key)
        merged = _entry_from_table_merge(prev, table)
        new_tables.append(merged)
        if prev is None:
            result.added += 1
        else:
            result.updated += 1
            if (
                prev.table_description == merged.table_description
                and prev.view_description == merged.view_description
            ):
                result.preserved += 1

    if prune_removed:
        for key in existing_map:
            if key not in seen_keys:
                result.removed += 1

    out = DataCatalog(
        version=1,
        generated_at=utc_now_iso(),
        schema_hash=_structural_hash(schema),
        tables=sorted(new_tables, key=lambda e: (e.schema_name, e.name)),
    )

    tmp = catalog_path.with_suffix(".yaml.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            out.model_dump(by_alias=True, mode="json", exclude_none=True),
            f,
            default_flow_style=False,
            sort_keys=False,
        )
    tmp.replace(catalog_path)
    logger.info(
        "Catalog sync: added=%s updated=%s removed=%s path=%s",
        result.added,
        result.updated,
        result.removed,
        catalog_path,
    )
    return result
