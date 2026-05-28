"""Tests for chart heuristics."""

import pytest
from intelligence_charts.heuristics import apply_heuristics
from intelligence_core.planner.models import ChartType, QueryPlan
from intelligence_sql.result import ColumnMetadata, QueryResult


@pytest.fixture
def plan_line():
    return QueryPlan(
        sql="SELECT date, rev FROM sales",
        chart_type=ChartType.LINE,
        x_field="date",
        y_field="rev",
        title="Revenue over time",
        explanation="Shows revenue.",
    )


@pytest.fixture
def plan_bar():
    return QueryPlan(
        sql="SELECT category, count FROM products",
        chart_type=ChartType.BAR,
        x_field="category",
        y_field="count",
        title="Products by category",
        explanation="Shows products.",
    )


def test_metric_card_override(plan_line):
    # One row, one numeric column -> forces metric card
    result = QueryResult(
        columns=[ColumnMetadata("total", "integer")],
        rows=[{"total": 42}],
        row_count=1,
        execution_time_ms=1.0,
        truncated=False,
    )

    heuristics = apply_heuristics(plan_line, result)
    assert heuristics.chart_type == ChartType.METRIC_CARD
    assert heuristics.y_field == "total"
    assert heuristics.x_field is None


def test_high_cardinality_bar_chart(plan_bar):
    # 25 rows with distinct categories -> forces table
    rows = [{"category": f"cat_{i}", "count": i} for i in range(25)]
    result = QueryResult(
        columns=[ColumnMetadata("category", "varchar"), ColumnMetadata("count", "integer")],
        rows=rows,
        row_count=25,
        execution_time_ms=1.0,
        truncated=False,
    )

    heuristics = apply_heuristics(plan_bar, result)
    assert heuristics.chart_type == ChartType.TABLE


def test_pie_chart_row_limit():
    plan = QueryPlan(
        sql="SELECT * FROM t",
        chart_type=ChartType.PIE,
        x_field="cat",
        y_field="val",
        title="pie",
        explanation="pie",
    )

    # >10 rows overrides pie to bar
    rows = [{"cat": f"c{i}", "val": i} for i in range(15)]
    result = QueryResult(
        columns=[ColumnMetadata("cat", "varchar"), ColumnMetadata("val", "integer")],
        rows=rows,
        row_count=15,
        execution_time_ms=1.0,
        truncated=False,
    )

    heuristics = apply_heuristics(plan, result)
    assert heuristics.chart_type == ChartType.BAR


def test_missing_fields_auto_detect(plan_line):
    # The LLM asks for "date" and "rev", but the query returned "ts" and "revenue"
    result = QueryResult(
        columns=[ColumnMetadata("ts", "timestamp"), ColumnMetadata("revenue", "float")],
        rows=[{"ts": "2024-01-01", "revenue": 100.0}],
        row_count=1,
        execution_time_ms=1.0,
        truncated=False,
    )

    heuristics = apply_heuristics(plan_line, result)
    assert heuristics.chart_type == ChartType.LINE
    assert heuristics.x_field == "ts"
    assert heuristics.y_field == "revenue"
