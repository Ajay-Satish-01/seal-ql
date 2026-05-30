from pathlib import Path

import pytest
from seal_core.catalog.models import DataCatalog
from seal_core.catalog.registry import DataCatalogRegistry
from seal_core.catalog.sync import sync_catalog
from seal_core.schema.models import ColumnInfo, ColumnType, DatabaseSchema, TableKind, TableSchema


def _table(name: str, kind: TableKind = TableKind.TABLE) -> TableSchema:
    return TableSchema(
        name=name,
        schema_name="public",
        kind=kind,
        columns=[
            ColumnInfo(
                name="id",
                data_type="bigint",
                normalized_type=ColumnType.INTEGER,
                nullable=False,
                is_primary_key=True,
            )
        ],
    )


@pytest.mark.asyncio
async def test_sync_adds_table_and_preserves_description(tmp_path: Path) -> None:
    path = tmp_path / "catalog.yaml"
    schema = DatabaseSchema(dialect="postgres", tables=[_table("orders")])

    await sync_catalog(schema, path)
    registry = DataCatalogRegistry()
    registry.load(path)
    entry = registry.get_entry("orders")
    assert entry is not None

    entry.table_description = "User curated"
    catalog = DataCatalog(
        version=1,
        tables=[entry],
    )
    import yaml

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(catalog.model_dump(by_alias=True, mode="json"), f)

    schema2 = DatabaseSchema(
        dialect="postgres",
        tables=[
            TableSchema(
                name="orders",
                schema_name="public",
                kind=TableKind.TABLE,
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="integer",
                        normalized_type=ColumnType.INTEGER,
                    ),
                    ColumnInfo(
                        name="amount",
                        data_type="numeric",
                        normalized_type=ColumnType.NUMERIC,
                    ),
                ],
            )
        ],
    )
    await sync_catalog(schema2, path)
    registry.load(path)
    updated = registry.get_entry("orders")
    assert updated is not None
    assert updated.table_description == "User curated"
    assert len(updated.columns) == 2


@pytest.mark.asyncio
async def test_sync_prunes_removed_table(tmp_path: Path) -> None:
    path = tmp_path / "catalog.yaml"
    schema = DatabaseSchema(
        dialect="postgres",
        tables=[_table("a"), _table("b")],
    )
    await sync_catalog(schema, path)
    schema2 = DatabaseSchema(dialect="postgres", tables=[_table("a")])
    result = await sync_catalog(schema2, path, prune_removed=True)
    assert result.removed >= 1
    registry = DataCatalogRegistry()
    registry.load(path)
    assert registry.get_entry("b") is None
