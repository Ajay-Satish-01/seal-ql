"""Shared test doubles for API route dependencies."""

from __future__ import annotations

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
    ) -> QueryPlan:
        return QueryPlan(
            sql="SELECT 1 as id",
            chart_type=ChartType.TABLE,
            x_field="id",
            y_field="id",
            title="Test",
            explanation="Test query",
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
