"""Response models for the Seal Python SDK.

These mirror the API response schemas, but are standalone Pydantic models
so the SDK has zero dependency on the internal server packages.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ChartType(StrEnum):
    """Chart types supported by the visualization engine."""

    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"
    TABLE = "table"
    METRIC_CARD = "metric_card"


class ColumnMetadata(BaseModel):
    """Metadata for a single result column."""

    name: str
    type: str = "str"
    nullable: bool = True


class ChartSpec(BaseModel):
    """Visualization specification returned by the API."""

    chart_type: ChartType
    vega_lite_spec: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    """The complete response from a /v1/query call."""

    sql: str
    columns: list[ColumnMetadata]
    results: list[dict[str, Any]]
    chart: ChartSpec | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Response from the /health endpoint."""

    status: str


class SchemaColumn(BaseModel):
    """A column in a database table schema."""

    name: str
    data_type: str
    normalized_type: str | None = None
    nullable: bool = True


class SchemaTable(BaseModel):
    """A table in the database schema."""

    name: str
    columns: list[SchemaColumn] = Field(default_factory=list)
    kind: str = "table"


class DatabaseSchema(BaseModel):
    """The full database schema returned by /v1/schema."""

    dialect: str
    tables: list[SchemaTable] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Response from POST /v1/chat."""

    session_id: str
    message: str
    sources: list[str] = Field(default_factory=list)
    sql: str | None = None
    results: list[dict[str, Any]] | None = None
    chart: ChartSpec | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CatalogResponse(BaseModel):
    """Response from GET /v1/catalog."""

    version: int = 1
    generated_at: str | None = None
    schema_hash: str | None = None
    tables: list[dict[str, Any]] = Field(default_factory=list)
