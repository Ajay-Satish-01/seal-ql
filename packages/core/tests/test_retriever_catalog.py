"""Context retriever catalog-aware fallback."""

from __future__ import annotations

from seal_core.catalog.models import CatalogEntry, DataCatalog
from seal_core.catalog.registry import DataCatalogRegistry
from seal_core.chat.retriever import ContextRetriever
from seal_core.schema.models import DatabaseSchema, TableSchema


def test_select_tables_catalog_description_fallback() -> None:
    schema = DatabaseSchema(
        dialect="postgres",
        tables=[
            TableSchema(name="orders", schema_name="public", columns=[]),
            TableSchema(name="users", schema_name="public", columns=[]),
        ],
    )
    registry = DataCatalogRegistry()
    registry._catalog = DataCatalog(
        tables=[
            CatalogEntry(
                schema_name="public",
                name="orders",
                table_description="Customer purchase orders and revenue",
            ),
            CatalogEntry(schema_name="public", name="users", table_description="App users"),
        ]
    )
    retriever = ContextRetriever()
    selected = retriever.select_tables(
        "revenue breakdown",
        schema,
        registry,
        max_tables=2,
    )
    assert selected == ["orders"]
