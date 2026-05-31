"""Tests for SchemaAwareEnhancer database_id behavior."""

from __future__ import annotations

import pytest
from seal_core.catalog.models import DataCatalog
from seal_core.catalog.registry import DataCatalogRegistry
from seal_core.enhancement.context import EnhancementContext
from seal_core.enhancement.schema_enhancer import SchemaAwareEnhancer
from seal_core.schema.models import ColumnInfo, ColumnType, DatabaseSchema, TableSchema


class _TrackingCatalog(DataCatalogRegistry):
    def __init__(self) -> None:
        super().__init__()
        self._catalog = DataCatalog()
        self.prompt_calls = 0

    def to_prompt_context(self, table_names: list[str]) -> str:
        self.prompt_calls += 1
        return super().to_prompt_context(table_names)


class _TrackingSemantic:
    def __init__(self) -> None:
        self.calls = 0

    def get_context_string(self) -> str:
        self.calls += 1
        return "semantic-context"


@pytest.mark.asyncio
async def test_schema_enhancer_uses_catalog_for_default_database() -> None:
    catalog = _TrackingCatalog()
    semantic = _TrackingSemantic()
    enhancer = SchemaAwareEnhancer(catalog=catalog, semantic_registry=semantic)
    schema = DatabaseSchema(
        dialect="postgres",
        tables=[
            TableSchema(
                name="orders",
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="int4",
                        normalized_type=ColumnType.INTEGER,
                        nullable=False,
                    )
                ],
            )
        ],
    )
    ctx = EnhancementContext(
        session_id="s1",
        turn_id="t1",
        stage="answer",
        user_message="show orders",
        base_system_prompt="BASE",
        database_schema=schema,
        metadata={"database_id": "default"},
    )
    prompt = await enhancer.enhance_system_prompt(ctx)
    assert "BASE" in prompt
    assert catalog.prompt_calls == 1
    assert semantic.calls == 1


@pytest.mark.asyncio
async def test_schema_enhancer_skips_catalog_for_non_default_database() -> None:
    catalog = _TrackingCatalog()
    semantic = _TrackingSemantic()
    enhancer = SchemaAwareEnhancer(catalog=catalog, semantic_registry=semantic)
    schema = DatabaseSchema(
        dialect="duckdb",
        tables=[
            TableSchema(
                name="events",
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="int",
                        normalized_type=ColumnType.INTEGER,
                        nullable=False,
                    )
                ],
            )
        ],
    )
    ctx = EnhancementContext(
        session_id="s1",
        turn_id="t1",
        stage="answer",
        user_message="show events",
        base_system_prompt="BASE",
        database_schema=schema,
        metadata={"database_id": "analytics"},
    )
    prompt = await enhancer.enhance_system_prompt(ctx)
    assert "BASE" in prompt
    assert "## Schema" in prompt
    assert catalog.prompt_calls == 0
    assert semantic.calls == 0
