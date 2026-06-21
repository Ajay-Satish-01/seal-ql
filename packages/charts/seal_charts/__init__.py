"""Chart specification generation engine.

Converts structured query plans and query results into valid Vega-Lite JSON specs.
"""

from seal_charts.engine import ChartEngine
from seal_charts.heuristics import HeuristicsResult, apply_heuristics
from seal_charts.models import ChartSpec, ChartStyleOptions
from seal_charts.specs import VEGA_LITE_SCHEMA
from seal_charts.styles import (
    ChartColorScheme,
    ChartTemplate,
    apply_chart_style,
    get_style_catalog,
)

__all__ = [
    "ChartEngine",
    "ChartColorScheme",
    "ChartSpec",
    "ChartStyleOptions",
    "ChartTemplate",
    "HeuristicsResult",
    "VEGA_LITE_SCHEMA",
    "apply_chart_style",
    "apply_heuristics",
    "get_style_catalog",
]
