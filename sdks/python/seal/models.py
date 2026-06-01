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


class ExecutionMetadata(BaseModel):
    """Execution metadata shared by query and chat.

    ``used_sql`` is True only after successful SQL execution. Chat may set ``sql_error``
    when the data path fails without populating ``sql``.
    """

    database_id: str = "default"
    row_count: int = 0
    execution_time_ms: float = 0
    truncated: bool = False
    warnings: list[str] = Field(default_factory=list)
    repair_attempts: int = 0
    used_sql: bool = False


class EnhancementMetadata(BaseModel):
    """Enhancement chain metadata on chat responses.

    Mirrors ``packages/core/seal_core/pipeline/models.py`` (SDK stays decoupled from core).
    """

    enabled: bool = False
    applied: list[str] = Field(default_factory=list)
    vector_skipped_reason: str | None = None
    unavailable_reason: str | None = None


class ChatMetadata(ExecutionMetadata):
    """Metadata on POST /v1/chat JSON responses."""

    enhancement: EnhancementMetadata = Field(default_factory=EnhancementMetadata)
    scope: dict[str, Any] | None = None
    refusal: bool | None = None
    sql_error: bool | None = None


class QueryResponse(BaseModel):
    """The complete response from a /v1/query call."""

    sql: str
    columns: list[ColumnMetadata]
    results: list[dict[str, Any]]
    chart: ChartSpec | None = None
    metadata: ExecutionMetadata | dict[str, Any] = Field(default_factory=ExecutionMetadata)


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
    columns: list[ColumnMetadata] | None = None
    chart: ChartSpec | None = None
    metadata: ChatMetadata | dict[str, Any] = Field(default_factory=ChatMetadata)


class CatalogResponse(BaseModel):
    """Response from GET /v1/catalog."""

    version: int = 1
    generated_at: str | None = None
    schema_hash: str | None = None
    tables: list[dict[str, Any]] = Field(default_factory=list)
