"""Chart heuristics for overriding and fixing LLM chart suggestions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from seal_core.planner.models import ChartType, QueryPlan

if TYPE_CHECKING:
    from seal_sql.result import QueryResult

logger = logging.getLogger(__name__)


@dataclass
class HeuristicsResult:
    """The result of applying heuristics to a query plan and result."""

    chart_type: ChartType
    x_field: str | None
    y_field: str | None
    color_field: str | None


def _find_field_in_result(field_name: str | None, result: QueryResult) -> str | None:
    """Find a field name in the query result, ignoring case."""
    if not field_name:
        return None

    lower_field = field_name.lower()
    for col in result.columns:
        if col.name.lower() == lower_field:
            return col.name
    return None


def _get_first_numeric_column(result: QueryResult, exclude: set[str] | None = None) -> str | None:
    """Find the first numeric column in the result."""
    exclude_set = exclude or set()
    for col in result.columns:
        if col.name in exclude_set:
            continue
        if col.type.lower() in (
            "integer",
            "bigint",
            "smallint",
            "decimal",
            "numeric",
            "real",
            "double precision",
            "float",
            "int",
            "int2",
            "int4",
            "int8",
            "float4",
            "float8",
        ):
            return col.name
    return None


def _get_first_categorical_or_date_column(
    result: QueryResult, exclude: set[str] | None = None
) -> str | None:
    """Find the first string, date, or timestamp column."""
    exclude_set = exclude or set()
    for col in result.columns:
        if col.name in exclude_set:
            continue
        if col.type.lower() in (
            "varchar",
            "text",
            "char",
            "date",
            "timestamp",
            "timestamp without time zone",
            "timestamp with time zone",
            "boolean",
        ):
            return col.name
    return None


def apply_heuristics(plan: QueryPlan, result: QueryResult) -> HeuristicsResult:
    """Apply heuristics to determine the best chart type and valid axes.

    Args:
        plan: The LLM-generated query plan.
        result: The actual executed query result.

    Returns:
        A HeuristicsResult with the validated chart type and fields.
    """

    # 1. Base case: No rows or no columns -> Table
    if not result.columns or not result.rows:
        return HeuristicsResult(ChartType.TABLE, None, None, None)

    # 2. Metric card: Single row, single numeric column
    if len(result.rows) == 1 and len(result.columns) == 1 and _get_first_numeric_column(result):
        return HeuristicsResult(ChartType.METRIC_CARD, None, result.columns[0].name, None)

    # Validate requested fields against actual result columns
    x_field = _find_field_in_result(plan.x_field, result)
    y_field = _find_field_in_result(plan.y_field, result)
    color_field = _find_field_in_result(plan.color_field, result)

    # 3. If missing essential fields, try to auto-detect
    if not x_field:
        x_field = _get_first_categorical_or_date_column(result)

    if not y_field:
        y_field = _get_first_numeric_column(result, exclude={x_field} if x_field else None)

    # 4. If we still don't have enough to plot, fallback to table
    if not x_field or not y_field:
        logger.info(
            f"Cannot find suitable x/y fields. Falling back to TABLE. "
            f"Requested: x={plan.x_field}, y={plan.y_field}"
        )
        return HeuristicsResult(ChartType.TABLE, None, None, None)

    chart_type = plan.chart_type

    # 5. Check cardinality for categorical data (e.g. Bar charts with 100 bars are useless)
    x_col_meta = next((c for c in result.columns if c.name == x_field), None)
    if x_col_meta and x_col_meta.type.lower() in ("varchar", "text", "char", "uuid", "boolean"):
        # Distinct values count
        distinct_x = len(set(str(row.get(x_field)) for row in result.rows))
        if distinct_x > 20:
            logger.info(
                f"High cardinality ({distinct_x} > 20) for categorical x-axis. Forcing TABLE."
            )
            chart_type = ChartType.TABLE

    # 6. Override pie charts with many slices
    if chart_type == ChartType.PIE and len(result.rows) > 10:
        logger.info(f"Too many rows ({len(result.rows)} > 10) for PIE chart. Converting to BAR.")
        chart_type = ChartType.BAR

    # 7. Safety check: ensure table fallback strips axes
    if chart_type == ChartType.TABLE:
        return HeuristicsResult(ChartType.TABLE, None, None, None)

    return HeuristicsResult(chart_type, x_field, y_field, color_field)
