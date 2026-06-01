"""Tests for QueryPlan validation."""

from seal_core.planner.models import ChartType, QueryPlan


def test_query_plan_allows_analyze_column_name() -> None:
    plan = QueryPlan(
        sql="SELECT analyze FROM metrics LIMIT 10",
        chart_type=ChartType.TABLE,
        title="t",
        explanation="e",
    )
    assert "analyze" in plan.sql


def test_query_plan_allows_pragma_column_name() -> None:
    plan = QueryPlan(
        sql="SELECT pragma FROM settings LIMIT 10",
        chart_type=ChartType.TABLE,
        title="t",
        explanation="e",
    )
    assert "pragma" in plan.sql


def test_query_plan_blocks_statement_analyze() -> None:
    try:
        QueryPlan(
            sql="ANALYZE users",
            chart_type=ChartType.TABLE,
            title="t",
            explanation="e",
        )
        raise AssertionError("expected validation error")
    except ValueError as e:
        assert "blocked pattern" in str(e).lower()


def test_query_plan_allows_semicolon_in_string_literal() -> None:
    """Semicolons inside string literals must not trigger multi-statement rejection."""
    plan = QueryPlan(
        sql="SELECT name FROM users WHERE status = 'active;pending' LIMIT 10",
        chart_type=ChartType.TABLE,
        title="t",
        explanation="e",
    )
    assert "active;pending" in plan.sql


def test_query_plan_blocks_real_multi_statement() -> None:
    """Actual multi-statement injection must still be caught."""
    try:
        QueryPlan(
            sql="SELECT 1; DROP TABLE users",
            chart_type=ChartType.TABLE,
            title="t",
            explanation="e",
        )
        raise AssertionError("expected validation error")
    except ValueError as e:
        assert "blocked pattern" in str(e).lower()
