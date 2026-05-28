import re
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

# Patterns that indicate destructive or dangerous SQL.
# These are blocked at the model level so Instructor's retry loop
# will automatically ask the LLM to regenerate safe SQL.
_BLOCKED_SQL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(ATTACH|DETACH)\b", re.IGNORECASE),
    re.compile(r"\b(PRAGMA)\b", re.IGNORECASE),
    re.compile(r";.*\S"),  # multiple statements
]


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
        for pattern in _BLOCKED_SQL_PATTERNS:
            match = pattern.search(v)
            if match:
                raise ValueError(
                    f"Generated SQL contains a blocked pattern: '{match.group()}'. "
                    "Only read-only SELECT queries are allowed."
                )
        return v

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
