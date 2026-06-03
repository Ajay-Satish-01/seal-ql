"""API Request and Response Models."""

from typing import Any, Self

from pydantic import BaseModel, Field, model_validator
from seal_charts.models import ChartSpec
from seal_core.guardrails.models import ScopeMetadata
from seal_core.pipeline.models import EnhancementMetadata, ExecutionMetadata
from seal_core.settings import get_settings
from seal_sql.result import ColumnMetadata

_MAX_QUERY_CHARS = 4000
_MAX_CHAT_MESSAGE_CHARS = 8000

DATABASE_ID_FIELD = Field(
    default="default",
    min_length=1,
    description="Registered database identifier (default: 'default').",
)


class QueryOutOfScopeDetail(BaseModel):
    """Structured HTTP 400 body when guardrails reject ``POST /v1/query``."""

    detail: str = Field(
        default="query_out_of_scope",
        description="Error code for programmatic clients.",
    )
    reason: str = Field(default="", description="Short classification reason.")
    suggested_queries: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Up to three example in-scope data questions.",
    )


class QueryOutOfScopeErrorResponse(BaseModel):
    """FastAPI error envelope for guardrails rejections on ``POST /v1/query``."""

    detail: QueryOutOfScopeDetail


class QueryRequest(BaseModel):
    """The incoming query request from a user."""

    query: str = Field(
        ...,
        max_length=_MAX_QUERY_CHARS,
        description="The natural language query to translate to SQL and execute.",
    )
    database_id: str = DATABASE_ID_FIELD


class QueryMetadata(ExecutionMetadata):
    """Execution metadata returned on successful /v1/query responses."""


class EnhancementInfo(EnhancementMetadata):
    """Re-exports core ``EnhancementMetadata`` for OpenAPI (see ``pipeline.models``)."""


class ChatMetadata(QueryMetadata):
    """Execution + enhancement metadata on /v1/chat JSON responses."""

    enhancement: EnhancementInfo = Field(default_factory=EnhancementInfo)
    scope: ScopeMetadata | None = Field(
        None, description="Guardrails scope decision when classified."
    )
    refusal: bool | None = Field(None, description="True when the turn was refused.")
    sql_error: bool | None = Field(None, description="True when SQL execution failed.")
    suggested_queries: list[str] | None = Field(
        default=None,
        max_length=3,
        exclude_if=lambda value: value is None,
        description="Example in-scope data questions on guardrails refusal.",
    )


class QueryResponse(BaseModel):
    """The complete response containing SQL, data, and visualization."""

    sql: str = Field(..., description="The generated and executed SQL query.")
    columns: list[ColumnMetadata] = Field(..., description="Metadata for the returned columns.")
    results: list[dict[str, Any]] = Field(..., description="The query result rows.")
    chart: ChartSpec | None = Field(
        None, description="The Vega-Lite chart specification, if applicable."
    )
    metadata: QueryMetadata | dict[str, Any] = Field(
        default_factory=QueryMetadata,
        description="Execution metadata (time, row count, limits, etc.).",
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="The health status of the API.")


class DatabaseInfo(BaseModel):
    """One entry in the configured database registry."""

    database_id: str = Field(..., description="Registered identifier passed as database_id.")
    dialect: str = Field(..., description="SQL dialect (postgres, duckdb, …).")
    is_default: bool = Field(..., description="True for the primary DATABASE_URL backend.")


class DatabasesListResponse(BaseModel):
    """Registered databases available for routing."""

    databases: list[DatabaseInfo] = Field(
        default_factory=list,
        description="Sorted list of configured database_id values.",
    )


class ChatMessageSchema(BaseModel):
    role: str = Field(..., description="user or assistant (system not allowed).")
    content: str = Field(
        ...,
        max_length=_MAX_CHAT_MESSAGE_CHARS,
        description="Message content.",
    )


class CatalogDescriptionItem(BaseModel):
    name: str
    schema_name: str = Field("public", alias="schema")
    table_description: str | None = None
    view_description: str | None = None

    model_config = {"populate_by_name": True}


class CatalogDescriptionsPatch(BaseModel):
    tables: list[CatalogDescriptionItem] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        max_length=_MAX_CHAT_MESSAGE_CHARS,
        description="Latest user message.",
    )
    session_id: str | None = Field(None, description="Conversation session id.")
    messages: list[ChatMessageSchema] | None = Field(
        None, description="Optional full history override."
    )
    stream: bool = Field(False, description="Stream final answer as SSE when true.")
    include_charts: bool = Field(
        False, description="When true, attach Vega-Lite chart if SQL runs."
    )
    enhancement: bool | None = Field(
        None,
        description=(
            "Override CHAT_ENHANCEMENT_ENABLED for this request. When true but the "
            "deployment has no active orchestrator, metadata.enhancement.enabled is false "
            "and metadata.enhancement.unavailable_reason is orchestrator_unavailable."
        ),
    )
    database_id: str = DATABASE_ID_FIELD

    @model_validator(mode="after")
    def validate_history_size(self) -> Self:
        if self.messages:
            total = sum(len(m.content) for m in self.messages)
            limit = get_settings().max_chat_history_chars
            if total > limit:
                msg = f"Chat history exceeds {limit} characters"
                raise ValueError(msg)
        return self


class ChatStreamMeta(ChatMetadata):
    """Flat JSON on the ``data:`` line of the ``seal.meta`` SSE event (stream=true)."""

    session_id: str = Field(..., description="Conversation session id.")
    sources: list[str] = Field(default_factory=list, description="Tables used in context.")
    sql: str | None = Field(None, description="Executed SQL when data was queried.")
    results: list[dict[str, Any]] | None = Field(None, description="Truncated result preview.")
    columns: list[ColumnMetadata] | None = Field(None, description="Column metadata.")
    chart: ChartSpec | None = Field(None, description="Chart when include_charts and SQL ran.")


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
    metadata: ChatMetadata | dict[str, Any] = Field(
        default_factory=ChatMetadata,
        description="Execution, enhancement, and guardrails metadata.",
    )


class SessionSummarySchema(BaseModel):
    session_id: str
    title: str | None = None
    database_id: str | None = None
    message_count: int = 0
    created_at: str = Field(..., description="ISO-8601 timestamp.")
    updated_at: str = Field(..., description="ISO-8601 timestamp.")


class SessionListResponse(BaseModel):
    sessions: list[SessionSummarySchema] = Field(default_factory=list)
    has_more: bool = Field(
        False,
        description="True when more sessions exist beyond this page.",
    )


class SessionMessageSchema(BaseModel):
    role: str
    content: str
    created_at: str | None = Field(None, description="ISO-8601 when available (postgres).")


class SessionDetailResponse(BaseModel):
    session_id: str
    title: str | None = None
    database_id: str | None = None
    messages: list[SessionMessageSchema] = Field(default_factory=list)
    created_at: str
    updated_at: str


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
