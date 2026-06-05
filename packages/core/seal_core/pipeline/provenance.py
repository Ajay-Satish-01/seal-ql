"""Explainability provenance derived from SQL validation and catalog context."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from seal_core.catalog.registry import DataCatalogRegistry
    from seal_core.pipeline.execute import ExecuteQueryResult
    from seal_core.schema.models import DatabaseSchema


def format_columns_used(columns_referenced: dict[str, set[str]]) -> list[str]:
    """Flatten SQLGlot column refs to ``table.column`` strings."""
    out: list[str] = []
    for table in sorted(columns_referenced):
        for col in sorted(columns_referenced[table]):
            out.append(f"{table}.{col}")
    return out


def _split_table_identifier(table_name: str) -> tuple[str | None, str]:
    if "." not in table_name:
        return None, table_name
    schema_part, bare_name = table_name.rsplit(".", 1)
    return schema_part, bare_name


def _schema_name_for_table(schema: DatabaseSchema, table_name: str) -> str | None:
    schema_hint, bare_name = _split_table_identifier(table_name)
    if schema_hint is not None:
        for table in schema.tables:
            if table.name == bare_name and table.schema_name == schema_hint:
                return table.schema_name
        return None

    matches = [table.schema_name for table in schema.tables if table.name == bare_name]
    if len(matches) == 1:
        return matches[0]
    return None


def build_catalog_matches(
    table_names: list[str],
    schema: DatabaseSchema,
    catalog: DataCatalogRegistry | None,
) -> list[dict[str, Any]]:
    """Catalog entries selected for planner context."""
    matches: list[dict[str, Any]] = []
    for name in table_names:
        _, bare_name = _split_table_identifier(name)
        schema_name = _schema_name_for_table(schema, name)
        entry = catalog.get_entry(bare_name, schema_name) if catalog and schema_name else None
        description = catalog.get_description(entry) if entry and catalog else None
        matches.append(
            {
                "name": bare_name,
                "schema": schema_name or "unknown",
                "description": description,
            }
        )
    return matches


def build_explainability_metadata(
    *,
    exec_result: ExecuteQueryResult | None,
    sources: list[str] | None,
    schema: DatabaseSchema | None,
    catalog: DataCatalogRegistry | None,
) -> dict[str, Any]:
    """Merge SQL and catalog provenance fields for response metadata."""
    payload: dict[str, Any] = {}
    if exec_result is not None:
        if exec_result.tables_used:
            payload["tables_used"] = list(exec_result.tables_used)
        if exec_result.columns_used:
            payload["columns_used"] = list(exec_result.columns_used)
    if sources and schema is not None:
        payload["catalog_matches"] = build_catalog_matches(sources, schema, catalog)
    return payload
