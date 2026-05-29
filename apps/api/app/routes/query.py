import logging

from fastapi import APIRouter, Depends, HTTPException
from intelligence_charts.engine import ChartEngine
from intelligence_core.planner.planner import QueryPlanner
from intelligence_core.schema.introspector import SchemaIntrospector
from intelligence_semantic.registry import SemanticRegistry
from intelligence_sql.executor import QueryExecutor
from intelligence_sql.sanitizer import SQLSanitizer
from intelligence_sql.validator import SQLValidator

from app.dependencies import (
    get_query_executor,
    get_query_planner,
    get_schema_introspector,
    get_semantic_registry,
)
from app.schemas import QueryRequest, QueryResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def execute_query(
    request: QueryRequest,
    introspector: SchemaIntrospector = Depends(get_schema_introspector),  # noqa: B008
    planner: QueryPlanner = Depends(get_query_planner),  # noqa: B008
    executor: QueryExecutor = Depends(get_query_executor),  # noqa: B008
    semantic_registry: SemanticRegistry = Depends(get_semantic_registry),  # noqa: B008
):
    """Translates natural language to SQL, executes it, and returns chart specs."""
    try:
        # 1. Introspect Schema
        schema = await introspector.introspect()

        # 2. Plan Query (LLM)
        plan = await planner.generate_plan(schema, request.query, semantic_registry)

        # Retry loop for repair
        max_attempts = 3
        current_attempt = 1

        while current_attempt <= max_attempts:
            try:
                # 3. Validate SQL
                validator = SQLValidator(schema)
                val_result = validator.validate(plan.sql)
                if not val_result.valid:
                    raise ValueError(f"SQL Validation failed: {val_result.errors}")

                # 4. Sanitize SQL
                sanitizer = SQLSanitizer()
                san_result = sanitizer.sanitize(val_result.normalized_sql)
                if not san_result.safe:
                    raise ValueError(
                        "SQL Sanitization failed: Query contains destructive operations."
                    )

                # 5. Execute SQL
                result = await executor.execute(san_result.sanitized_sql)
                break  # Success! Break out of the retry loop

            except Exception as e:
                if current_attempt >= max_attempts:
                    logger.error(f"Failed after {max_attempts} attempts. Last error: {str(e)}")
                    raise HTTPException(status_code=400, detail=f"Query failed: {str(e)}") from e

                logger.debug(
                    f"Attempt {current_attempt} failed. Attempting repair. Error: {str(e)}"
                )
                # Use the planner to repair the plan based on the error message
                plan = await planner.repair_plan(request.query, plan.sql, str(e))
                current_attempt += 1

        # 6. Generate Chart Spec
        chart_spec = ChartEngine.generate(plan, result)

        # 7. Build final response
        return QueryResponse(
            sql=san_result.sanitized_sql,
            columns=result.columns,
            results=result.rows,
            chart=chart_spec,
            metadata={
                "row_count": result.row_count,
                "execution_time_ms": result.execution_time_ms,
                "truncated": result.truncated,
                "warnings": san_result.warnings,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to execute query")
        raise HTTPException(status_code=500, detail=str(e)) from e
