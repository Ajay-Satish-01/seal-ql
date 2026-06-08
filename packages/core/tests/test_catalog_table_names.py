"""Tests for catalog/schema table name helpers."""

from __future__ import annotations

from seal_core.catalog.models import CatalogEntry, DataCatalog
from seal_core.catalog.registry import DataCatalogRegistry
from seal_core.catalog.table_names import (
    catalog_table_names,
    merge_table_name_hints,
    schema_table_names_from_schema,
)
from seal_core.schema.models import DatabaseSchema, TableSchema


def test_catalog_table_names_from_registry() -> None:
    registry = DataCatalogRegistry()
    registry._catalog = DataCatalog(
        tables=[
            CatalogEntry(name="orders", schema_name="public"),
            CatalogEntry(name="products", schema_name="public"),
        ]
    )
    assert catalog_table_names(registry) == ("orders", "products")


def test_merge_table_name_hints_dedupes_case_insensitive() -> None:
    merged = merge_table_name_hints(("Orders",), ("orders", "products"))
    assert merged == ("Orders", "products")


def test_schema_table_names_from_schema() -> None:
    schema = DatabaseSchema(
        tables=[TableSchema(name="events", schema_name="public", columns=[])],
        dialect="postgres",
    )
    assert schema_table_names_from_schema(schema) == ("events",)
