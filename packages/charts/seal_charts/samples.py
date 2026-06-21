"""Canonical styled Vega-Lite sample specs for docs and tests."""

from __future__ import annotations

from typing import Any

from seal_core.planner.models import ChartType

from seal_charts.heuristics import HeuristicsResult
from seal_charts.models import ChartStyleOptions
from seal_charts.specs import VEGA_LITE_SCHEMA
from seal_charts.styles import ChartColorScheme, ChartTemplate, apply_chart_style

_BAR_ROWS = [
    {"category": "Electronics", "total_revenue": 45200},
    {"category": "Clothing", "total_revenue": 32100},
    {"category": "Books", "total_revenue": 18700},
]

_BASE_BAR_SPEC: dict[str, Any] = {
    "$schema": VEGA_LITE_SCHEMA,
    "title": "Revenue by category",
    "width": "container",
    "height": "container",
    "data": {"values": _BAR_ROWS},
    "mark": {"type": "bar", "tooltip": True},
    "encoding": {
        "x": {"field": "category", "type": "nominal"},
        "y": {"field": "total_revenue", "type": "quantitative"},
    },
}

_BAR_HEURISTICS = HeuristicsResult(
    chart_type=ChartType.BAR,
    x_field="category",
    y_field="total_revenue",
    color_field=None,
)


def styled_bar_sample(
    template: ChartTemplate = ChartTemplate.ROUNDED,
    color_scheme: ChartColorScheme = ChartColorScheme.TABLEAU10,
) -> dict[str, Any]:
    """Return a styled bar chart Vega-Lite spec."""
    style = ChartStyleOptions(template=template, color_scheme=color_scheme)
    return apply_chart_style(_BASE_BAR_SPEC, style, _BAR_HEURISTICS)


SAMPLE_SPECS: dict[str, dict[str, Any]] = {
    "bar_rounded_tableau10": styled_bar_sample(),
    "bar_minimal_category10": styled_bar_sample(
        template=ChartTemplate.MINIMAL,
        color_scheme=ChartColorScheme.CATEGORY10,
    ),
    "bar_bold_blues": styled_bar_sample(
        template=ChartTemplate.BOLD,
        color_scheme=ChartColorScheme.BLUES,
    ),
}
