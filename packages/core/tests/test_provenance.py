"""Tests for explainability provenance helpers."""

from __future__ import annotations

from seal_core.pipeline.execute import ExecuteQueryResult
from seal_core.pipeline.provenance import (
    build_catalog_matches,
    build_explainability_metadata,
    format_columns_used,
)
from seal_core.planner.models import ChartType, QueryPlan
from seal_core.schema.models import ColumnInfo, ColumnType, DatabaseSchema, TableSchema
from seal_sql.result import ColumnMetadata


def test_format_columns_used() -> None:
    assert format_columns_used({"orders": {"id", "total"}, "products": {"sku"}}) == [
        "orders.id",
        "orders.total",
        "products.sku",
    ]


def test_build_explainability_metadata_from_exec_result() -> None:
    exec_result = ExecuteQueryResult(
        sql="SELECT id FROM orders",
        columns=[ColumnMetadata("id", "int")],
        rows=[{"id": 1}],
        plan=QueryPlan(
            sql="SELECT id FROM orders",
            chart_type=ChartType.TABLE,
            title="t",
            explanation="e",
        ),
        row_count=1,
        execution_time_ms=1.0,
        truncated=False,
        tables_used=["orders"],
        columns_used=["orders.id"],
    )
    meta = build_explainability_metadata(
        exec_result=exec_result,
        sources=None,
        schema=None,
        catalog=None,
    )
    assert meta["tables_used"] == ["orders"]
    assert meta["columns_used"] == ["orders.id"]


def test_build_catalog_matches_empty_without_catalog() -> None:
    schema = DatabaseSchema(
        dialect="postgres",
        tables=[
            TableSchema(
                name="orders",
                schema_name="public",
                columns=[
                    ColumnInfo(name="id", data_type="int", normalized_type=ColumnType.INTEGER)
                ],
            )
        ],
    )
    matches = build_catalog_matches(["orders"], schema, None)
    assert matches == [{"name": "orders", "schema": "public", "description": None}]
