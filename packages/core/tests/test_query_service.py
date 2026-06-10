"""Unit tests for QueryService orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from seal_core.catalog.models import DataCatalog
from seal_core.catalog.registry import DataCatalogRegistry
from seal_core.database.registry import DatabaseBundle, DatabaseRegistry, UnknownDatabaseError
from seal_core.guardrails.models import ScopeResult
from seal_core.pipeline.query_service import QueryOutOfScopeError, QueryService
from seal_core.planner.models import ChartType, QueryPlan
from seal_core.reasoning.models import ReasoningMetadata
from seal_core.reasoning.orchestrator import build_default_orchestrator
from seal_core.schema.models import DatabaseSchema
from seal_sql.result import ColumnMetadata, QueryResult


class _MockIntrospector:
    async def introspect(self) -> DatabaseSchema:
        return DatabaseSchema(tables=[], dialect="postgres")


class _MockPlanner:
    async def generate_plan(self, *_args: object, **_kwargs: object) -> QueryPlan:
        return QueryPlan(
            sql="SELECT 1 as id",
            chart_type=ChartType.TABLE,
            x_field="id",
            y_field="id",
            title="Test",
            explanation="Test query",
        )

    async def repair_plan(self, *_args: object, **_kwargs: object) -> QueryPlan:
        return QueryPlan(
            sql="SELECT 1 as id",
            chart_type=ChartType.TABLE,
            title="Test",
            explanation="Repaired",
        )


class _MockExecutor:
    async def execute(self, sql: str) -> QueryResult:
        return QueryResult(
            columns=[ColumnMetadata("id", "int")],
            rows=[{"id": 1}],
            row_count=1,
            execution_time_ms=1.0,
            truncated=False,
            sql=sql,
        )


class _MockSemanticRegistry:
    def get_context_string(self) -> str:
        return ""


class _MockDataCatalog(DataCatalogRegistry):
    def __init__(self) -> None:
        super().__init__()
        self._catalog = DataCatalog()


def _make_service() -> QueryService:
    registry = DatabaseRegistry(
        {
            "default": DatabaseBundle(
                database_id="default",
                dialect="postgres",
                url="mock://default",
                introspector=_MockIntrospector(),
                executor=_MockExecutor(),
            )
        }
    )
    return QueryService(
        planner=_MockPlanner(),
        registry=registry,
        data_catalog=_MockDataCatalog(),
        semantic_registry=_MockSemanticRegistry(),
        reasoning_orchestrator=build_default_orchestrator(),
    )


@pytest.mark.asyncio
async def test_execute_raises_unknown_database() -> None:
    service = _make_service()
    with pytest.raises(UnknownDatabaseError):
        await service.execute(query="count rows", database_id="nonexistent")


@pytest.mark.asyncio
async def test_execute_raises_out_of_scope() -> None:
    service = _make_service()
    with (
        patch(
            "seal_core.pipeline.query_service.classify_scope",
            new=AsyncMock(
                return_value=ScopeResult(in_scope=False, reason="off-topic", source="heuristic")
            ),
        ),
        pytest.raises(QueryOutOfScopeError) as exc_info,
    ):
        await service.execute(query="write me a poem", database_id="default")
    assert exc_info.value.scope.reason == "off-topic"


@pytest.mark.asyncio
async def test_execute_returns_clarification_without_sql() -> None:
    service = _make_service()
    clarification = ReasoningMetadata(
        clarification_required=True,
        clarifying_questions=["Which metric?"],
        layers_applied=["clarification"],
    )
    with (
        patch(
            "seal_core.pipeline.query_service.classify_scope",
            new=AsyncMock(return_value=ScopeResult(in_scope=True, reason="ok", source="heuristic")),
        ),
        patch.object(
            service._reasoning,
            "run_pre",
            new=AsyncMock(return_value=clarification),
        ),
    ):
        result = await service.execute(query="show me trends", database_id="default")

    assert result.sql == ""
    assert result.results == []
    assert result.metadata["used_sql"] is False
    assert result.metadata["reasoning"]["clarification_required"] is True
    assert result.message


@pytest.mark.asyncio
async def test_execute_success_path() -> None:
    service = _make_service()
    with patch(
        "seal_core.pipeline.query_service.classify_scope",
        new=AsyncMock(return_value=ScopeResult(in_scope=True, reason="ok", source="heuristic")),
    ):
        result = await service.execute(
            query="How many orders were placed last month?",
            database_id="default",
        )

    assert result.sql
    assert result.metadata["used_sql"] is True
    assert result.metadata["database_id"] == "default"
    assert isinstance(result.metadata.get("reasoning"), dict)
    assert len(result.results) == 1


@pytest.mark.asyncio
async def test_execute_does_not_call_pipeline_when_clarifying() -> None:
    service = _make_service()
    pipeline = AsyncMock()
    clarification = ReasoningMetadata(
        clarification_required=True,
        clarifying_questions=["Which table?"],
    )
    with (
        patch(
            "seal_core.pipeline.query_service.classify_scope",
            new=AsyncMock(return_value=ScopeResult(in_scope=True, reason="ok", source="heuristic")),
        ),
        patch.object(service._reasoning, "run_pre", new=AsyncMock(return_value=clarification)),
        patch("seal_core.pipeline.query_service.execute_natural_language_query", new=pipeline),
    ):
        await service.execute(query="trends", database_id="default")
    pipeline.assert_not_called()
