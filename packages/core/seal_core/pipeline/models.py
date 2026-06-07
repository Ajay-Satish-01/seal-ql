"""Shared execution metadata for query and chat responses.

**JSON chat** (``stream=false``): execution + enhancement live under ``response.metadata``.

**SSE** (``stream=true``): the same fields appear flat on the ``seal.meta`` event payload
(see ``validate_stream_meta_event`` in ``validate_metadata.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from seal_core.database.config import DEFAULT_DATABASE_ID, is_default_database_id
from seal_core.guardrails.models import ScopeMetadata
from seal_core.reasoning.models import ReasoningMetadata

if TYPE_CHECKING:
    from seal_core.pipeline.execute import ExecuteQueryResult

VectorSkippedReason = Literal["non_default_database", "vector_store_disabled"]
EnhancementUnavailableReason = Literal["orchestrator_unavailable"]

VECTOR_SKIPPED_NON_DEFAULT: VectorSkippedReason = "non_default_database"
VECTOR_SKIPPED_VECTOR_STORE_DISABLED: VectorSkippedReason = "vector_store_disabled"
ENHANCEMENT_UNAVAILABLE_ORCHESTRATOR: EnhancementUnavailableReason = "orchestrator_unavailable"


class EnhancementMetadata(BaseModel):
    """Enhancement chain state surfaced on chat metadata and SSE seal.meta."""

    enabled: bool = False
    applied: list[str] = Field(default_factory=list)
    vector_skipped_reason: VectorSkippedReason | None = None
    unavailable_reason: EnhancementUnavailableReason | None = Field(
        None,
        description="Set when enhancement was requested but the orchestrator is not active.",
    )


class CatalogMatchItem(BaseModel):
    """Catalog entry included in planner context."""

    name: str
    schema_name: str = Field("public", alias="schema")
    description: str | None = None

    model_config = {"populate_by_name": True}


class ExecutionMetadata(BaseModel):
    """Execution fields shared by /v1/query and /v1/chat.

    ``used_sql`` is True only when SQL was executed successfully (``exec_result`` present).
    Failed planner/executor paths set ``sql_error`` on chat metadata and leave ``used_sql`` False.
    """

    database_id: str = DEFAULT_DATABASE_ID
    row_count: int = 0
    execution_time_ms: float = 0
    truncated: bool = False
    warnings: list[str] = Field(default_factory=list)
    repair_attempts: int = 0
    used_sql: bool = False
    tables_used: list[str] = Field(
        default_factory=list,
        description="Tables referenced in executed SQL (SQLGlot validation).",
    )
    columns_used: list[str] = Field(
        default_factory=list,
        description="Columns referenced in executed SQL as table.column.",
    )
    catalog_matches: list[CatalogMatchItem] = Field(
        default_factory=list,
        description="Catalog entries selected for planner context.",
    )

    @classmethod
    def from_execute_result(
        cls,
        *,
        database_id: str,
        exec_result: ExecuteQueryResult | None,
        used_sql: bool,
        catalog_matches: list[CatalogMatchItem] | list[dict[str, Any]] | None = None,
    ) -> ExecutionMetadata:
        if exec_result is None:
            return cls(database_id=database_id, used_sql=used_sql)
        matches: list[CatalogMatchItem] = []
        if catalog_matches:
            for item in catalog_matches:
                if isinstance(item, CatalogMatchItem):
                    matches.append(item)
                else:
                    matches.append(CatalogMatchItem.model_validate(item))
        return cls(
            database_id=database_id,
            row_count=exec_result.row_count,
            execution_time_ms=exec_result.execution_time_ms,
            truncated=exec_result.truncated,
            warnings=list(exec_result.warnings),
            repair_attempts=exec_result.repair_attempts,
            used_sql=used_sql,
            tables_used=list(exec_result.tables_used),
            columns_used=list(exec_result.columns_used),
            catalog_matches=matches,
        )


def build_enhancement_metadata(
    *,
    enabled: bool,
    applied: list[str] | None,
    database_id: str,
    vector_rag_available: bool,
    orchestrator_available: bool,
    enhancement_requested: bool = False,
) -> EnhancementMetadata:
    """Build unified enhancement block.

    ``vector_skipped_reason`` is set only when enhancement is enabled for the turn and
    vector RAG cannot run (non-default ``database_id``, or vector store disabled on default).

    ``unavailable_reason`` is set when enhancement was requested but no orchestrator is
    configured (not when enhancement is intentionally off for a turn, e.g. guardrails refusal).
    """
    reason: VectorSkippedReason | None = None
    if enabled:
        if not is_default_database_id(database_id):
            reason = VECTOR_SKIPPED_NON_DEFAULT
        elif not vector_rag_available:
            reason = VECTOR_SKIPPED_VECTOR_STORE_DISABLED
    unavailable: EnhancementUnavailableReason | None = None
    if enhancement_requested and not orchestrator_available:
        unavailable = ENHANCEMENT_UNAVAILABLE_ORCHESTRATOR
    return EnhancementMetadata(
        enabled=enabled,
        applied=list(applied or []),
        vector_skipped_reason=reason,
        unavailable_reason=unavailable,
    )


def build_chat_metadata(
    *,
    database_id: str,
    exec_result: ExecuteQueryResult | None,
    used_sql: bool,
    enhancement_enabled: bool,
    applied: list[str] | None = None,
    scope: ScopeMetadata | dict[str, Any] | None = None,
    refusal: bool = False,
    sql_error: bool = False,
    suggested_queries: list[str] | None = None,
    reasoning: ReasoningMetadata | dict[str, Any] | None = None,
    vector_rag_available: bool,
    orchestrator_available: bool,
    enhancement_requested: bool = False,
    catalog_matches: list[CatalogMatchItem] | list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Merge execution + enhancement (+ optional scope/refusal) for chat JSON/SSE."""
    payload: dict[str, Any] = ExecutionMetadata.from_execute_result(
        database_id=database_id,
        exec_result=exec_result,
        used_sql=used_sql,
        catalog_matches=catalog_matches,
    ).model_dump()
    for key in ("tables_used", "columns_used", "catalog_matches"):
        if not payload.get(key):
            payload.pop(key, None)
    enh = build_enhancement_metadata(
        enabled=enhancement_enabled,
        applied=applied,
        database_id=database_id,
        vector_rag_available=vector_rag_available,
        enhancement_requested=enhancement_requested,
        orchestrator_available=orchestrator_available,
    )
    payload["enhancement"] = enh.model_dump(exclude_none=True)
    if scope is not None:
        payload["scope"] = (
            scope.model_dump(exclude_none=True) if isinstance(scope, ScopeMetadata) else scope
        )
    if refusal:
        payload["refusal"] = True
    if suggested_queries:
        payload["suggested_queries"] = suggested_queries[:3]
    if sql_error:
        payload["sql_error"] = True
    if reasoning is not None:
        payload["reasoning"] = (
            reasoning.model_dump(exclude_none=True)
            if isinstance(reasoning, ReasoningMetadata)
            else reasoning
        )
    return payload


def build_stream_meta_event(
    *,
    session_id: str,
    database_id: str,
    exec_result: ExecuteQueryResult | None,
    used_sql: bool,
    enhancement_enabled: bool,
    applied: list[str] | None,
    sources: list[str],
    sql: str | None,
    results: list[dict[str, Any]] | None,
    columns: list[dict[str, Any]] | None,
    chart: dict[str, Any] | None,
    scope: ScopeMetadata | dict[str, Any] | None,
    refusal: bool = False,
    sql_error: bool = False,
    suggested_queries: list[str] | None = None,
    reasoning: ReasoningMetadata | dict[str, Any] | None = None,
    vector_rag_available: bool,
    orchestrator_available: bool,
    enhancement_requested: bool = False,
    catalog_matches: list[CatalogMatchItem] | list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Payload for SSE ``seal.meta`` aligned with chat JSON metadata execution fields."""
    event: dict[str, Any] = {
        "session_id": session_id,
        "sources": sources,
        "sql": sql,
        "results": results,
        "columns": columns,
        "chart": chart,
        "scope": scope,
    }
    event.update(
        build_chat_metadata(
            database_id=database_id,
            exec_result=exec_result,
            used_sql=used_sql,
            enhancement_enabled=enhancement_enabled,
            applied=applied,
            scope=None,
            refusal=refusal,
            sql_error=sql_error,
            suggested_queries=suggested_queries,
            reasoning=reasoning,
            vector_rag_available=vector_rag_available,
            enhancement_requested=enhancement_requested,
            orchestrator_available=orchestrator_available,
            catalog_matches=catalog_matches,
        )
    )
    return event
