"""Orchestration for stateless ``POST /v1/query`` turns."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field
from seal_charts.engine import ChartEngine
from seal_sql.result import QueryResult

from seal_core.catalog.table_names import (
    catalog_table_names,
    merge_table_name_hints,
    schema_table_names_from_schema,
)
from seal_core.chat.retriever import ContextRetriever
from seal_core.database.config import planner_resources_for_database
from seal_core.guardrails.models import ScopeMetadata, ScopeResult
from seal_core.guardrails.scope import classify_scope
from seal_core.pipeline.execute import ExecuteQueryResult, execute_natural_language_query
from seal_core.pipeline.models import ExecutionMetadata
from seal_core.pipeline.provenance import build_catalog_matches
from seal_core.pipeline.trust import is_trust_explainability_enabled
from seal_core.pipeline.validate_metadata import enforce_query_metadata
from seal_core.reasoning.clarification_response import (
    clarification_message,
    clarification_metadata_reasoning,
)
from seal_core.reasoning.merge import merge_reasoning_metadata
from seal_core.reasoning.models import (
    DatabaseCapabilities,
    ReasoningContext,
    ReasoningMetadata,
    ReasoningPhase,
    format_reasoning_message,
    normalize_reasoning_clarification,
    should_return_clarification,
)

if TYPE_CHECKING:
    from seal_semantic.registry import SemanticRegistry

    from seal_core.catalog.registry import DataCatalogRegistry
    from seal_core.database.registry import DatabaseRegistry
    from seal_core.planner.planner import QueryPlanner
    from seal_core.reasoning.orchestrator import ReasoningOrchestrator

logger = logging.getLogger(__name__)


class QueryOutOfScopeError(Exception):
    """Raised when guardrails reject a query before execution."""

    def __init__(self, scope: ScopeResult) -> None:
        self.scope = scope
        super().__init__(scope.reason)


class QueryTurnResult(BaseModel):
    """Successful or clarification-only query turn payload."""

    message: str | None = None
    sql: str = ""
    columns: list[Any] = Field(default_factory=list)
    results: list[dict[str, Any]] = Field(default_factory=list)
    chart: Any | None = None
    sources: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _build_query_metadata(
    *,
    database_id: str,
    exec_result: ExecuteQueryResult | None,
    used_sql: bool,
    scope: ScopeMetadata,
    reasoning: ReasoningMetadata,
    catalog_matches: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    metadata = ExecutionMetadata.from_execute_result(
        database_id=database_id,
        exec_result=exec_result,
        used_sql=used_sql,
        catalog_matches=catalog_matches,
    ).model_dump()
    metadata["scope"] = scope.model_dump(exclude_none=True)
    metadata["reasoning"] = reasoning.model_dump(exclude_none=True)
    return metadata


class QueryService:
    """Shared query-path orchestration for the API and integrators."""

    def __init__(
        self,
        *,
        planner: QueryPlanner,
        registry: DatabaseRegistry,
        data_catalog: DataCatalogRegistry,
        semantic_registry: SemanticRegistry,
        reasoning_orchestrator: ReasoningOrchestrator,
        context_retriever: ContextRetriever | None = None,
    ) -> None:
        self._planner = planner
        self._registry = registry
        self._data_catalog = data_catalog
        self._semantic_registry = semantic_registry
        self._reasoning = reasoning_orchestrator
        self._retriever = context_retriever or ContextRetriever()

    async def execute(self, *, query: str, database_id: str) -> QueryTurnResult:
        bundle = self._registry.get(database_id)
        catalog_names = catalog_table_names(self._data_catalog)

        schema = await bundle.introspector.introspect()
        schema_table_names = schema_table_names_from_schema(schema)
        table_name_hints = merge_table_name_hints(catalog_names, schema_table_names)

        scope = await classify_scope(
            query,
            channel="query",
            schema_table_names=table_name_hints,
        )
        if not scope.in_scope:
            raise QueryOutOfScopeError(scope)

        scope_meta = ScopeMetadata.from_result(scope)
        capabilities = DatabaseCapabilities.from_bundle(
            database_id=database_id,
            dialect=bundle.dialect,
        )

        pre_ctx = ReasoningContext(
            route="query",
            user_message=query,
            database_capabilities=capabilities,
            phase=ReasoningPhase.PRE_EXECUTION,
            schema_table_count=len(schema.tables) if hasattr(schema, "tables") else None,
            schema_table_names=table_name_hints,
        )
        pre_reasoning = normalize_reasoning_clarification(await self._reasoning.run_pre(pre_ctx))
        if should_return_clarification(pre_reasoning):
            return self._clarification_result(
                database_id=database_id,
                scope=scope_meta,
                reasoning=pre_reasoning,
            )

        semantic, catalog = planner_resources_for_database(
            database_id,
            catalog=self._data_catalog,
            semantic_registry=self._semantic_registry,
        )

        table_names = self._retriever.select_tables(
            query,
            schema,
            catalog,
            full_schema=True,
        )

        exec_result = await execute_natural_language_query(
            question=query,
            schema=schema,
            planner=self._planner,
            executor=bundle.executor,
            semantic_registry=semantic,
            data_catalog=catalog,
            table_names=table_names,
        )

        result = QueryResult(
            columns=exec_result.columns,
            rows=exec_result.rows,
            row_count=exec_result.row_count,
            execution_time_ms=exec_result.execution_time_ms,
            truncated=exec_result.truncated,
            sql=exec_result.sql,
        )
        chart_spec = ChartEngine.generate(exec_result.plan, result)

        post_ctx = ReasoningContext(
            route="query",
            user_message=query,
            database_capabilities=capabilities,
            phase=ReasoningPhase.POST_EXECUTION,
            exec_result=exec_result,
            schema_table_count=len(schema.tables),
            schema_table_names=table_name_hints,
        )
        post_reasoning = await self._reasoning.run_post(post_ctx)
        planner_explanation = exec_result.plan.explanation
        planner_note = ReasoningMetadata(
            research_notes=(
                [planner_explanation]
                if is_trust_explainability_enabled()
                and planner_explanation
                and planner_explanation != "No explanation provided."
                else []
            ),
            layers_applied=["query_planner"],
        )
        reasoning = merge_reasoning_metadata(pre_reasoning, post_reasoning, planner_note)
        assistant_message = format_reasoning_message(reasoning, include_inferred=False)
        if (
            not assistant_message.strip()
            and is_trust_explainability_enabled()
            and planner_explanation
            and planner_explanation != "No explanation provided."
        ):
            assistant_message = planner_explanation

        catalog_matches = build_catalog_matches(table_names, schema, catalog)
        metadata = _build_query_metadata(
            database_id=database_id,
            exec_result=exec_result,
            used_sql=True,
            scope=scope_meta,
            reasoning=reasoning,
            catalog_matches=catalog_matches,
        )
        enforce_query_metadata(metadata)

        return QueryTurnResult(
            message=assistant_message or None,
            sql=exec_result.sql,
            columns=exec_result.columns,
            results=exec_result.rows,
            chart=chart_spec,
            sources=table_names,
            metadata=metadata,
        )

    def _clarification_result(
        self,
        *,
        database_id: str,
        scope: ScopeMetadata,
        reasoning: ReasoningMetadata,
    ) -> QueryTurnResult:
        metadata = ExecutionMetadata(
            database_id=database_id,
            used_sql=False,
        ).model_dump()
        metadata["scope"] = scope.model_dump(exclude_none=True)
        metadata["reasoning"] = clarification_metadata_reasoning(reasoning)
        enforce_query_metadata(metadata)
        return QueryTurnResult(
            message=clarification_message(reasoning, include_inferred=False),
            metadata=metadata,
        )
