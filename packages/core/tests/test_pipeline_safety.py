"""Pipeline wiring for SQL validation and sanitization."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from seal_core.pipeline.execute import execute_natural_language_query
from seal_core.planner.models import ChartType, QueryPlan
from seal_core.schema.models import (
    ColumnInfo,
    ColumnType,
    DatabaseSchema,
    TableKind,
    TableSchema,
)
from seal_sql.boundary import SqlBoundaryResult, format_boundary_errors, validate_and_sanitize
from seal_sql.result import ColumnMetadata, QueryResult


def _minimal_schema() -> DatabaseSchema:
    return DatabaseSchema(
        dialect="postgres",
        tables=[
            TableSchema(
                name="users",
                kind=TableKind.TABLE,
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="INTEGER",
                        normalized_type=ColumnType.INTEGER,
                    ),
                ],
            ),
        ],
    )


@pytest.mark.asyncio
async def test_pipeline_uses_validate_and_sanitize() -> None:
    schema = DatabaseSchema(dialect="duckdb", tables=[])
    plan = QueryPlan(
        sql="SELECT 1",
        chart_type=ChartType.TABLE,
        title="t",
        explanation="e",
    )
    planner = MagicMock()
    planner.generate_plan = AsyncMock(return_value=plan)
    planner.repair_plan = AsyncMock(return_value=plan)

    executor = MagicMock()
    executor.execute = AsyncMock(
        return_value=QueryResult(
            columns=[ColumnMetadata("c", "int")],
            rows=[{"c": 1}],
            row_count=1,
            execution_time_ms=1.0,
            truncated=False,
            sql="SELECT 1",
        )
    )

    with patch("seal_core.pipeline.execute.validate_and_sanitize") as boundary_fn:
        boundary_fn.return_value = SqlBoundaryResult(
            valid=True,
            executable_sql="SELECT 1 LIMIT 10000",
            warnings=[],
        )

        await execute_natural_language_query(
            question="q",
            schema=schema,
            planner=planner,
            executor=executor,
        )

        boundary_fn.assert_called_once_with(plan.sql, schema)


@pytest.mark.asyncio
async def test_pipeline_surfaces_boundary_warnings() -> None:
    schema = DatabaseSchema(dialect="postgres", tables=[])
    plan = QueryPlan(
        sql="SELECT 1",
        chart_type=ChartType.TABLE,
        title="t",
        explanation="e",
    )
    planner = MagicMock()
    planner.generate_plan = AsyncMock(return_value=plan)

    executor = MagicMock()
    executor.execute = AsyncMock(
        return_value=QueryResult(
            columns=[],
            rows=[],
            row_count=0,
            execution_time_ms=0.0,
            truncated=False,
            sql="SELECT 1",
        )
    )

    with patch("seal_core.pipeline.execute.validate_and_sanitize") as boundary_fn:
        boundary_fn.return_value = SqlBoundaryResult(
            valid=True,
            executable_sql="SELECT 1 LIMIT 10000",
            warnings=["warn-a", "warn-b"],
        )

        result = await execute_natural_language_query(
            question="q",
            schema=schema,
            planner=planner,
            executor=executor,
        )

    assert result.warnings == ["warn-a", "warn-b"]


def test_validate_and_sanitize_integration() -> None:
    """Real boundary path without mocks or database."""
    schema = _minimal_schema()
    result = validate_and_sanitize("SELECT id FROM users", schema)
    assert result.valid
    assert "LIMIT" in result.executable_sql.upper()


def test_validate_and_sanitize_blocks_for_update() -> None:
    result = validate_and_sanitize("SELECT id FROM users FOR UPDATE", _minimal_schema())
    assert not result.valid


def test_format_boundary_errors_joins_multiple() -> None:
    assert format_boundary_errors(["err-a", "err-b"]) == "err-a; err-b"


@pytest.mark.asyncio
async def test_pipeline_surfaces_all_boundary_errors() -> None:
    """Repair loop feedback must include every validation error, not only the first."""
    schema = _minimal_schema()
    plan = QueryPlan(
        sql="SELECT bad FROM users",
        chart_type=ChartType.TABLE,
        title="t",
        explanation="e",
    )
    planner = MagicMock()
    planner.generate_plan = AsyncMock(return_value=plan)
    planner.repair_plan = AsyncMock(return_value=plan)

    with patch("seal_core.pipeline.execute.validate_and_sanitize") as boundary_fn:
        boundary_fn.return_value = SqlBoundaryResult(
            valid=False,
            errors=["unknown column: bad", "unknown table: missing"],
        )
        with pytest.raises(ValueError, match="unknown column: bad; unknown table: missing"):
            await execute_natural_language_query(
                question="q",
                schema=schema,
                planner=planner,
                executor=MagicMock(),
            )
