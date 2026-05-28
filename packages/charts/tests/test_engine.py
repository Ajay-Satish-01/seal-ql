"""Tests for the ChartEngine orchestrator."""

from intelligence_charts.engine import ChartEngine
from intelligence_core.planner.models import ChartType, QueryPlan
from intelligence_sql.result import ColumnMetadata, QueryResult


def test_engine_generates_valid_vega_spec():
    plan = QueryPlan(
        sql="SELECT date, sales FROM data",
        chart_type=ChartType.LINE,
        x_field="date",
        y_field="sales",
        title="Sales Trend",
        explanation="Sales over time.",
    )

    result = QueryResult(
        columns=[ColumnMetadata("date", "date"), ColumnMetadata("sales", "integer")],
        rows=[{"date": "2024-01-01", "sales": 100}],
        row_count=1,
        execution_time_ms=1.0,
        truncated=False,
    )

    spec = ChartEngine.generate(plan, result)

    assert spec.chart_type == ChartType.LINE
    assert spec.metadata["requested_chart_type"] == ChartType.LINE
    assert spec.vega_lite_spec["$schema"] == "https://vega.github.io/schema/vega-lite/v5.json"
    assert spec.vega_lite_spec["title"] == "Sales Trend"
    assert spec.vega_lite_spec["mark"]["type"] == "line"
    assert spec.vega_lite_spec["encoding"]["x"]["field"] == "date"
    assert spec.vega_lite_spec["encoding"]["x"]["type"] == "temporal"
    assert spec.vega_lite_spec["encoding"]["y"]["field"] == "sales"
    assert spec.vega_lite_spec["encoding"]["y"]["type"] == "quantitative"


def test_engine_handles_table_fallback():
    plan = QueryPlan(
        sql="SELECT a, b, c FROM data",
        chart_type=ChartType.TABLE,  # Requested as table
        x_field="a",
        y_field="b",
        title="Raw Data",
        explanation="Raw data dump.",
    )

    result = QueryResult(
        columns=[
            ColumnMetadata("a", "varchar"),
            ColumnMetadata("b", "varchar"),
            ColumnMetadata("c", "varchar"),
        ],
        rows=[{"a": "1", "b": "2", "c": "3"}],
        row_count=1,
        execution_time_ms=1.0,
        truncated=False,
    )

    spec = ChartEngine.generate(plan, result)

    assert spec.chart_type == ChartType.TABLE
    assert spec.vega_lite_spec == {}  # No vega spec for tables
