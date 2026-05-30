"""API Request and Response Models."""

from typing import Any

from pydantic import BaseModel, Field
from seal_charts.models import ChartSpec
from seal_sql.result import ColumnMetadata


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


class ChatMessageSchema(BaseModel):
    role: str = Field(..., description="user, assistant, or system")
    content: str = Field(..., description="Message content.")


class ChatRequest(BaseModel):
    message: str = Field(..., description="Latest user message.")
    session_id: str | None = Field(None, description="Conversation session id.")
    messages: list[ChatMessageSchema] | None = Field(
        None, description="Optional full history override."
    )
    stream: bool = Field(False, description="Stream final answer as SSE when true.")
    include_charts: bool = Field(
        False, description="When true, attach Vega-Lite chart if SQL runs."
    )
    enhancement: bool | None = Field(
        None, description="Override CHAT_ENHANCEMENT_ENABLED for this request."
    )
    database_id: str = Field("default", description="Target database identifier.")


class ChatResponse(BaseModel):
    session_id: str = Field(..., description="Session id for follow-up messages.")
    message: str = Field(..., description="Assistant natural language answer.")
    sources: list[str] = Field(
        default_factory=list, description="Tables used in retrieved context."
    )
    sql: str | None = Field(None, description="Executed SQL when data was queried.")
    results: list[dict[str, Any]] | None = Field(None, description="Truncated result preview.")
    columns: list[ColumnMetadata] | None = Field(None, description="Column metadata.")
    chart: ChartSpec | None = Field(None, description="Chart when include_charts and SQL ran.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Enhancement and timing.")


class CatalogSyncResponse(BaseModel):
    added: int
    updated: int
    preserved: int
    removed: int
    path: str


class CatalogResponse(BaseModel):
    version: int
    generated_at: str | None = None
    schema_hash: str | None = None
    tables: list[dict[str, Any]] = Field(default_factory=list)
