"""Tests for the ChartEngine orchestrator."""

from seal_charts import VEGA_LITE_SCHEMA
from seal_charts.engine import ChartEngine
from seal_charts.models import ChartStyleOptions
from seal_charts.styles import ChartColorScheme, ChartTemplate
from seal_core.planner.models import ChartType, QueryPlan
from seal_sql.result import ColumnMetadata, QueryResult


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
    assert "template" not in spec.metadata
    assert "color_scheme" not in spec.metadata
    assert "color" not in spec.vega_lite_spec.get("encoding", {})
    assert spec.vega_lite_spec["$schema"] == VEGA_LITE_SCHEMA
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


def test_engine_applies_style_when_requested():
    plan = QueryPlan(
        sql="SELECT category, total FROM data",
        chart_type=ChartType.BAR,
        x_field="category",
        y_field="total",
        title="By category",
        explanation="Bar chart.",
    )
    result = QueryResult(
        columns=[
            ColumnMetadata("category", "varchar"),
            ColumnMetadata("total", "integer"),
        ],
        rows=[{"category": "A", "total": 10}],
        row_count=1,
        execution_time_ms=1.0,
        truncated=False,
    )
    style = ChartStyleOptions(
        template=ChartTemplate.ROUNDED,
        color_scheme=ChartColorScheme.TABLEAU10,
    )

    spec = ChartEngine.generate(plan, result, style=style)

    assert spec.metadata["template"] == "rounded"
    assert spec.metadata["color_scheme"] == "tableau10"
    assert spec.vega_lite_spec["mark"]["cornerRadiusEnd"] == 4
    assert spec.vega_lite_spec["encoding"]["color"]["scale"]["scheme"] == "tableau10"
