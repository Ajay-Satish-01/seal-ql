from enum import StrEnum

from pydantic import BaseModel, Field


class ChartType(StrEnum):
    """Supported chart types for visualization."""

    LINE = "line"
    BAR = "bar"
    SCATTER = "scatter"
    TABLE = "table"
    PIE = "pie"
    AREA = "area"
    METRIC_CARD = "metric_card"


class QueryPlan(BaseModel):
    """
    Structured output from the LLM query planner.
    Contains the generated SQL, requested chart configuration, and an explanation.
    """

    sql: str = Field(
        ...,
        description="The SQL query to execute. Must be valid SQL for the target database dialect.",
    )
    chart_type: ChartType = Field(
        ..., description="The recommended chart type for visualizing the results."
    )
    x_field: str = Field(
        ..., description="The column name to use for the X-axis (or primary category)."
    )
    y_field: str = Field(
        ..., description="The column name to use for the Y-axis (or primary metric)."
    )
    color_field: str | None = Field(
        default=None, description="Optional column name to use for coloring/grouping the data."
    )
    title: str = Field(..., description="A concise, human-readable title for the chart/results.")
    explanation: str = Field(
        ...,
        description="A brief explanation of what the query does and how it answers the "
        "user's question.",
    )
