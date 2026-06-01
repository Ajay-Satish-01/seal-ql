"""Shared NL → SQL execution pipeline for query and chat routes."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from seal_sql.boundary import format_boundary_errors, validate_and_sanitize

if TYPE_CHECKING:
    from seal_sql.executor import QueryExecutor
    from seal_sql.result import ColumnMetadata, QueryResult

    from seal_core.planner.models import QueryPlan
    from seal_core.planner.planner import QueryPlanner
    from seal_core.schema.models import DatabaseSchema

logger = logging.getLogger(__name__)


@dataclass
class ExecuteQueryResult:
    """Result of a validated and executed natural-language query."""

    sql: str
    columns: list[ColumnMetadata]
    rows: list[dict[str, Any]]
    plan: QueryPlan
    row_count: int
    execution_time_ms: float
    truncated: bool
    warnings: list[str] = field(default_factory=list)
    repair_attempts: int = 0


async def execute_natural_language_query(
    *,
    question: str,
    schema: DatabaseSchema,
    planner: QueryPlanner,
    executor: QueryExecutor,
    semantic_registry: Any | None = None,
    data_catalog: Any | None = None,
    table_names: list[str] | None = None,
    max_attempts: int = 3,
) -> ExecuteQueryResult:
    """Plan SQL, validate, sanitize, execute with repair loop."""
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")

    plan = await planner.generate_plan(
        schema,
        question,
        semantic_registry=semantic_registry,
        data_catalog=data_catalog,
        table_names=table_names,
    )

    boundary_result = None
    result: QueryResult | None = None
    repair_attempts = 0

    for attempt in range(1, max_attempts + 1):
        try:
            boundary_result = validate_and_sanitize(plan.sql, schema)
            if not boundary_result.valid:
                raise ValueError(format_boundary_errors(boundary_result.errors))

            result = await executor.execute(boundary_result.executable_sql)
            repair_attempts = attempt - 1
            break
        except Exception as e:
            if attempt >= max_attempts:
                logger.error("Failed after %s attempts: %s", max_attempts, e)
                raise
            logger.debug("Attempt %s failed, repairing: %s", attempt, e)
            plan = await planner.repair_plan(
                question,
                plan.sql,
                str(e),
                schema=schema,
                semantic_registry=semantic_registry,
                data_catalog=data_catalog,
                table_names=table_names,
            )
            repair_attempts = attempt

    assert boundary_result is not None and result is not None

    return ExecuteQueryResult(
        sql=boundary_result.executable_sql,
        columns=result.columns,
        rows=result.rows,
        plan=plan,
        row_count=result.row_count,
        execution_time_ms=result.execution_time_ms,
        truncated=result.truncated,
        warnings=list(boundary_result.warnings),
        repair_attempts=repair_attempts,
    )
