"""Chart engine orchestrator."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from seal_charts.heuristics import apply_heuristics
from seal_charts.models import ChartSpec, ChartStyleOptions
from seal_charts.specs import build_vega_lite_spec
from seal_charts.styles import apply_chart_style

if TYPE_CHECKING:
    from seal_core.planner.models import QueryPlan
    from seal_sql.result import QueryResult

logger = logging.getLogger(__name__)


class ChartEngine:
    """Orchestrates chart generation from a query plan and execution result."""

    @classmethod
    def generate(
        cls,
        plan: QueryPlan,
        result: QueryResult,
        style: ChartStyleOptions | None = None,
    ) -> ChartSpec:
        """Generate a valid chart spec.

        Args:
            plan: The LLM-generated query plan (contains requested chart type and axes).
            result: The actual database query result.
            style: Optional chart template and color scheme.

        Returns:
            A ChartSpec object containing the determined chart type and the Vega-Lite JSON spec.
        """
        # 1. Apply heuristics to validate and potentially override LLM suggestions
        heuristics_result = apply_heuristics(plan, result)

        # 2. Build the Vega-Lite spec based on the validated fields
        vega_spec = build_vega_lite_spec(plan.title, heuristics_result, result)

        # 3. Apply template and color scheme only when explicitly requested
        if vega_spec and style is not None:
            vega_spec = apply_chart_style(vega_spec, style, heuristics_result)

        metadata = {
            "requested_chart_type": plan.chart_type,
            "applied_chart_type": heuristics_result.chart_type,
            "x_field": heuristics_result.x_field,
            "y_field": heuristics_result.y_field,
            "color_field": heuristics_result.color_field,
        }
        if style is not None:
            metadata["template"] = style.template.value
            metadata["color_scheme"] = style.color_scheme.value

        return ChartSpec(
            chart_type=heuristics_result.chart_type, vega_lite_spec=vega_spec, metadata=metadata
        )
