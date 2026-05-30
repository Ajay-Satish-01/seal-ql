"""Chart specification generation engine.

Converts structured query plans and query results into valid Vega-Lite v5 JSON specs.
"""

from seal_charts.engine import ChartEngine
from seal_charts.heuristics import HeuristicsResult, apply_heuristics
from seal_charts.models import ChartSpec

__all__ = [
    "ChartEngine",
    "ChartSpec",
    "HeuristicsResult",
    "apply_heuristics",
]
