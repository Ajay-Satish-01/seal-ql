from unittest.mock import AsyncMock, MagicMock

import pytest
from seal_core.pipeline.execute import execute_natural_language_query
from seal_core.planner.models import ChartType, QueryPlan
from seal_core.schema.models import DatabaseSchema


@pytest.mark.asyncio
async def test_pipeline_executes_with_catalog() -> None:
    schema = DatabaseSchema(dialect="postgres", tables=[])
    plan = QueryPlan(
        sql="SELECT 1",
        chart_type=ChartType.TABLE,
        title="t",
        explanation="e",
    )
    planner = MagicMock()
    planner.generate_plan = AsyncMock(return_value=plan)
    planner.repair_plan = AsyncMock(return_value=plan)

    catalog = MagicMock()
    catalog.to_prompt_context = MagicMock(return_value="catalog ctx")

    from seal_sql.result import ColumnMetadata, QueryResult

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

    result = await execute_natural_language_query(
        question="count rows",
        schema=schema,
        planner=planner,
        executor=executor,
        data_catalog=catalog,
    )
    assert result.sql
    planner.generate_plan.assert_awaited_once()
    assert planner.generate_plan.await_args.kwargs.get("data_catalog") is catalog
