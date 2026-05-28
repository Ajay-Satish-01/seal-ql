"""Chart engine orchestrator."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from intelligence_charts.heuristics import apply_heuristics
from intelligence_charts.models import ChartSpec
from intelligence_charts.specs import build_vega_lite_spec

if TYPE_CHECKING:
    from intelligence_core.planner.models import QueryPlan
    from intelligence_sql.result import QueryResult

logger = logging.getLogger(__name__)


class ChartEngine:
    """Orchestrates chart generation from a query plan and execution result."""

    @classmethod
    def generate(cls, plan: QueryPlan, result: QueryResult) -> ChartSpec:
        """Generate a valid chart spec.

        Args:
            plan: The LLM-generated query plan (contains requested chart type and axes).
            result: The actual database query result.

        Returns:
            A ChartSpec object containing the determined chart type and the Vega-Lite JSON spec.
        """
        # 1. Apply heuristics to validate and potentially override LLM suggestions
        heuristics_result = apply_heuristics(plan, result)

        # 2. Build the Vega-Lite spec based on the validated fields
        vega_spec = build_vega_lite_spec(plan.title, heuristics_result, result)

        metadata = {
            "requested_chart_type": plan.chart_type,
            "applied_chart_type": heuristics_result.chart_type,
            "x_field": heuristics_result.x_field,
            "y_field": heuristics_result.y_field,
            "color_field": heuristics_result.color_field,
        }

        return ChartSpec(
            chart_type=heuristics_result.chart_type, vega_lite_spec=vega_spec, metadata=metadata
        )
