"""Chart specification models.

These models define the structure of the final output from the chart engine.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from seal_core.planner.models import ChartType  # noqa: TCH002


class ChartSpec(BaseModel):
    """The final visualization specification.

    Attributes:
        chart_type: The determined type of chart (line, bar, table, etc.).
        vega_lite_spec: A JSON-serializable dictionary containing a valid Vega-Lite spec.
            If chart_type is 'table' or 'metric_card', this will be empty (as they are
            rendered natively by the UI, not via Vega-Lite).
        metadata: Additional metadata for rendering (e.g., suggested titles, formatting hints).
    """

    chart_type: ChartType
    vega_lite_spec: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
