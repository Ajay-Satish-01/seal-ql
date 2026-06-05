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


def _schema_name_for_table(schema: DatabaseSchema, table_name: str) -> str:
    for table in schema.tables:
        if table.name == table_name:
            return table.schema_name
    return "public"


def build_catalog_matches(
    table_names: list[str],
    schema: DatabaseSchema,
    catalog: DataCatalogRegistry | None,
) -> list[dict[str, Any]]:
    """Catalog entries selected for planner context."""
    matches: list[dict[str, Any]] = []
    for name in table_names:
        schema_name = _schema_name_for_table(schema, name)
        entry = catalog.get_entry(name, schema_name) if catalog else None
        description = catalog.get_description(entry) if entry and catalog else None
        matches.append(
            {
                "name": name,
                "schema": schema_name,
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
