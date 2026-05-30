"""Shared test doubles for API route dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from seal_core.catalog.models import DataCatalog
from seal_core.catalog.registry import DataCatalogRegistry
from seal_core.chat.models import ChatMessage
from seal_core.planner.models import ChartType, QueryPlan
from seal_core.schema.models import DatabaseSchema
from seal_sql.result import ColumnMetadata, QueryResult


class MockIntrospector:
    async def introspect(self) -> DatabaseSchema:
        return DatabaseSchema(tables=[], dialect="postgres")


class MockPlanner:
    async def generate_plan(
        self,
        schema: DatabaseSchema,
        query: str,
        semantic_registry: object | None = None,
        data_catalog: object | None = None,
        table_names: list[str] | None = None,
    ) -> QueryPlan:
        return QueryPlan(
            sql="SELECT 1 as id",
            chart_type=ChartType.TABLE,
            x_field="id",
            y_field="id",
            title="Test",
            explanation="Test query",
        )

    async def repair_plan(
        self,
        question: str,
        original_sql: str,
        error_message: str,
        *,
        schema: DatabaseSchema | None = None,
        semantic_registry: object | None = None,
        data_catalog: object | None = None,
        table_names: list[str] | None = None,
    ) -> QueryPlan:
        return QueryPlan(
            sql="SELECT 1 as id",
            chart_type=ChartType.TABLE,
            title="Test",
            explanation="Repaired",
        )


class MockExecutor:
    async def execute(self, sql: str) -> QueryResult:
        return QueryResult(
            columns=[ColumnMetadata("id", "int")],
            rows=[{"id": 1}],
            row_count=1,
            execution_time_ms=1.0,
            truncated=False,
            sql=sql,
        )


class MockSemanticRegistry:
    def get_context_string(self) -> str:
        return ""


class MockDataCatalog(DataCatalogRegistry):
    def __init__(self) -> None:
        super().__init__()
        self._catalog = DataCatalog()


class MockChatService:
    async def handle_json(
        self,
        *,
        message: str,
        session_id: str | None,
        messages_override: list[ChatMessage] | None,
        include_charts: bool,
        enhancement_enabled: bool | None,
        schema: Any,
    ) -> Any:
        from seal_core.chat.service import ChatResult

        sid = session_id or "test-session"
        return ChatResult(
            session_id=sid,
            message=f"Echo: {message}",
            sources=["mock_table"],
            metadata={"used_sql": False, "enhancement": {}},
        )

    async def handle_stream(
        self,
        *,
        message: str,
        session_id: str | None,
        messages_override: list[ChatMessage] | None,
        include_charts: bool,
        enhancement_enabled: bool | None,
        schema: Any,
    ) -> AsyncIterator[str]:
        yield 'event: seal.meta\ndata: {"session_id":"test-session"}\n\n'
        yield 'data: {"choices":[{"delta":{"content":"Hi"}}]}\n\n'
        yield "data: [DONE]\n\n"
