"""Generate demo fixtures for apps/docs using the real ChartEngine."""

from __future__ import annotations

import json
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "packages" / "core"))
sys.path.insert(0, str(root_dir / "packages" / "sql"))
sys.path.insert(0, str(root_dir / "packages" / "charts"))

from seal_charts.engine import ChartEngine  # noqa: E402
from seal_core.planner.models import ChartType, QueryPlan  # noqa: E402
from seal_sql.result import ColumnMetadata, QueryResult  # noqa: E402

OUTPUT_PATH = root_dir / "apps" / "docs" / "src" / "data" / "demo-fixtures.json"

METADATA_BASE = {
    "row_count": 0,
    "execution_time_ms": 24.5,
    "truncated": False,
    "warnings": [],
}


def _response(
    *,
    query: str,
    label: str,
    preset_id: str,
    sql: str,
    columns: list[ColumnMetadata],
    rows: list[dict],
    plan: QueryPlan,
) -> dict:
    result = QueryResult(
        columns=columns,
        rows=rows,
        row_count=len(rows),
        execution_time_ms=METADATA_BASE["execution_time_ms"],
        truncated=False,
    )
    chart = ChartEngine.generate(plan, result)
    meta = {**METADATA_BASE, "row_count": len(rows)}
    return {
        "id": preset_id,
        "label": label,
        "query": query,
        "response": {
            "sql": sql,
            "columns": [{"name": c.name, "type": c.type, "nullable": c.nullable} for c in columns],
            "results": rows,
            "chart": {
                "chart_type": chart.chart_type.value,
                "vega_lite_spec": chart.vega_lite_spec,
                "metadata": chart.metadata,
            },
            "metadata": meta,
        },
    }


def build_presets() -> list[dict]:
    revenue_rows = [
        {"category": "Electronics", "total_revenue": 45200.5},
        {"category": "Clothing", "total_revenue": 28100.0},
        {"category": "Home", "total_revenue": 19850.75},
        {"category": "Sports", "total_revenue": 12400.0},
    ]
    bar = _response(
        query="Show total revenue by product category",
        label="Revenue by category",
        preset_id="revenue-by-category",
        sql=(
            "SELECT p.category, SUM(o.amount) AS total_revenue "
            "FROM orders o JOIN products p ON o.product_id = p.id "
            "WHERE o.status = 'completed' "
            "GROUP BY p.category ORDER BY total_revenue DESC LIMIT 10000"
        ),
        columns=[
            ColumnMetadata("category", "varchar"),
            ColumnMetadata("total_revenue", "numeric"),
        ],
        rows=revenue_rows,
        plan=QueryPlan(
            sql="SELECT p.category, SUM(o.amount) AS total_revenue FROM orders o LIMIT 10000",
            chart_type=ChartType.BAR,
            x_field="category",
            y_field="total_revenue",
            title="Revenue by Product Category",
            explanation="Bar chart of revenue grouped by category.",
        ),
    )

    hourly_rows = [
        {"hour": "2024-01-01T08:00:00", "event_count": 120},
        {"hour": "2024-01-01T09:00:00", "event_count": 185},
        {"hour": "2024-01-01T10:00:00", "event_count": 240},
        {"hour": "2024-01-01T11:00:00", "event_count": 310},
        {"hour": "2024-01-01T12:00:00", "event_count": 275},
    ]
    line = _response(
        query="Show hourly event counts for the last day",
        label="Hourly events",
        preset_id="hourly-events",
        sql=(
            "SELECT bucket AS hour, SUM(event_count) AS event_count "
            "FROM events_hourly GROUP BY bucket ORDER BY bucket LIMIT 10000"
        ),
        columns=[
            ColumnMetadata("hour", "timestamptz"),
            ColumnMetadata("event_count", "int8"),
        ],
        rows=hourly_rows,
        plan=QueryPlan(
            sql="SELECT hour, event_count FROM events_hourly LIMIT 10000",
            chart_type=ChartType.LINE,
            x_field="hour",
            y_field="event_count",
            title="Hourly Event Volume",
            explanation="Line chart of events over time.",
        ),
    )

    region_rows = [
        {"region": "North", "orders": 142},
        {"region": "South", "orders": 98},
        {"region": "East", "orders": 115},
        {"region": "West", "orders": 87},
    ]
    pie = _response(
        query="Orders by region as a pie chart",
        label="Orders by region",
        preset_id="orders-by-region",
        sql=(
            "SELECT region, COUNT(*) AS orders FROM orders "
            "GROUP BY region ORDER BY orders DESC LIMIT 10000"
        ),
        columns=[
            ColumnMetadata("region", "varchar"),
            ColumnMetadata("orders", "int8"),
        ],
        rows=region_rows,
        plan=QueryPlan(
            sql="SELECT region, orders FROM orders LIMIT 10000",
            chart_type=ChartType.PIE,
            x_field="region",
            y_field="orders",
            title="Orders by Region",
            explanation="Pie chart of order distribution.",
        ),
    )

    product_rows = [
        {
            "product_name": "Wireless Headphones",
            "category": "Electronics",
            "total_revenue": 18500.0,
            "total_orders": 92,
        },
        {
            "product_name": "Running Shoes",
            "category": "Sports",
            "total_revenue": 14200.0,
            "total_orders": 71,
        },
        {
            "product_name": "Desk Lamp",
            "category": "Home",
            "total_revenue": 8900.0,
            "total_orders": 178,
        },
    ]
    table = _response(
        query="Top products by revenue and order count",
        label="Product performance table",
        preset_id="product-performance",
        sql=(
            "SELECT product_name, category, total_revenue, total_orders "
            "FROM product_performance ORDER BY total_revenue DESC LIMIT 10"
        ),
        columns=[
            ColumnMetadata("product_name", "varchar"),
            ColumnMetadata("category", "varchar"),
            ColumnMetadata("total_revenue", "numeric"),
            ColumnMetadata("total_orders", "int8"),
        ],
        rows=product_rows,
        plan=QueryPlan(
            sql=(
                "SELECT product_name, category, total_revenue, total_orders "
                "FROM product_performance LIMIT 10000"
            ),
            chart_type=ChartType.TABLE,
            x_field="product_name",
            y_field="total_revenue",
            title="Top Products",
            explanation="Tabular product performance.",
        ),
    )

    metric_rows = [{"total_revenue": 105551.25}]
    metric = _response(
        query="What is total completed order revenue?",
        label="Total revenue KPI",
        preset_id="total-revenue-metric",
        sql=(
            "SELECT SUM(amount) AS total_revenue FROM orders WHERE status = 'completed' LIMIT 10000"
        ),
        columns=[ColumnMetadata("total_revenue", "numeric")],
        rows=metric_rows,
        plan=QueryPlan(
            sql="SELECT SUM(amount) AS total_revenue FROM orders LIMIT 10000",
            chart_type=ChartType.METRIC_CARD,
            x_field=None,
            y_field="total_revenue",
            title="Total Revenue",
            explanation="Single KPI for total revenue.",
        ),
    )

    scatter_rows = [
        {"region": "North", "avg_order_value": 85.2, "customer_count": 12},
        {"region": "South", "avg_order_value": 120.5, "customer_count": 8},
        {"region": "East", "avg_order_value": 65.0, "customer_count": 22},
        {"region": "West", "avg_order_value": 200.1, "customer_count": 5},
    ]
    scatter = _response(
        query="Customer count vs average order value by segment",
        label="Customer segments",
        preset_id="customer-segments",
        sql=(
            "SELECT region, AVG(total_spent) AS avg_order_value, COUNT(*) AS customer_count "
            "FROM customer_summary GROUP BY region LIMIT 10000"
        ),
        columns=[
            ColumnMetadata("region", "varchar"),
            ColumnMetadata("avg_order_value", "numeric"),
            ColumnMetadata("customer_count", "int8"),
        ],
        rows=scatter_rows,
        plan=QueryPlan(
            sql="SELECT avg_order_value, customer_count FROM customer_summary LIMIT 10000",
            chart_type=ChartType.SCATTER,
            x_field="avg_order_value",
            y_field="customer_count",
            title="Customer Segments",
            explanation="Scatter plot of segment metrics.",
        ),
    )

    return [bar, line, pie, table, metric, scatter]


def main() -> None:
    presets = build_presets()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w") as f:
        json.dump({"version": "1.0.0", "presets": presets}, f, indent=2)
    print(f"✅ Wrote {len(presets)} demo presets to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
