"""API Request and Response Models."""

from typing import Any

from intelligence_charts.models import ChartSpec
from intelligence_sql.result import ColumnMetadata
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """The incoming query request from a user."""

    query: str = Field(
        ..., description="The natural language query to translate to SQL and execute."
    )
    database_id: str = Field("default", description="The identifier for the target database.")


class QueryResponse(BaseModel):
    """The complete response containing SQL, data, and visualization."""

    sql: str = Field(..., description="The generated and executed SQL query.")
    columns: list[ColumnMetadata] = Field(..., description="Metadata for the returned columns.")
    results: list[dict[str, Any]] = Field(..., description="The query result rows.")
    chart: ChartSpec | None = Field(
        None, description="The Vega-Lite chart specification, if applicable."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Execution metadata (time, row count, limits, etc.)."
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="The health status of the API.")
