"""Chart specification generation engine.

Converts structured query plans and query results into valid Vega-Lite v5 JSON specs.
"""

from intelligence_charts.engine import ChartEngine
from intelligence_charts.heuristics import HeuristicsResult, apply_heuristics
from intelligence_charts.models import ChartSpec

__all__ = [
    "ChartEngine",
    "ChartSpec",
    "HeuristicsResult",
    "apply_heuristics",
]
