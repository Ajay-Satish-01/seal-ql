from enum import StrEnum

from pydantic import BaseModel, Field, field_validator
from seal_sql.planner_patterns import planner_sql_validation_error


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
        description="The SQL query to execute. Must be a read-only SELECT query. "
        "Never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or TRUNCATE.",
    )

    @field_validator("sql")
    @classmethod
    def sql_must_be_read_only(cls, v: str) -> str:
        """Reject any SQL that contains destructive or multi-statement patterns."""
        if error := planner_sql_validation_error(v):
            raise ValueError(error)
        return v

    chart_type: ChartType = Field(
        default=ChartType.TABLE,
        description="The recommended chart type for visualizing the results.",
    )

    @field_validator("chart_type", mode="before")
    @classmethod
    def clean_chart_type(cls, v: str) -> str:
        """Fix small models outputting $defs.ChartType.pie instead of just pie."""
        if isinstance(v, str) and v.startswith("$defs.ChartType."):
            return v.split(".")[-1]
        return v

    x_field: str | None = Field(
        default=None, description="The column name to use for the X-axis (or primary category)."
    )
    y_field: str | None = Field(
        default=None, description="The column name to use for the Y-axis (or primary metric)."
    )
    color_field: str | None = Field(
        default=None, description="Optional column name to use for coloring/grouping the data."
    )
    title: str = Field(
        default="Query Results",
        description="A concise, human-readable title for the chart/results.",
    )
    explanation: str = Field(
        default="No explanation provided.",
        description="A brief explanation of what the query does and how it answers the "
        "user's question.",
    )
