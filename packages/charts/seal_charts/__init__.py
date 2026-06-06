"""Chart specification generation engine.

Converts structured query plans and query results into valid Vega-Lite JSON specs.
"""

from seal_charts.engine import ChartEngine
from seal_charts.heuristics import HeuristicsResult, apply_heuristics
from seal_charts.models import ChartSpec
from seal_charts.specs import VEGA_LITE_SCHEMA

__all__ = [
    "ChartEngine",
    "ChartSpec",
    "HeuristicsResult",
    "VEGA_LITE_SCHEMA",
    "apply_heuristics",
]
