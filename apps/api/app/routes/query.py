import logging

from fastapi import APIRouter, Depends, HTTPException
from intelligence_charts.engine import ChartEngine
from intelligence_core.planner.planner import QueryPlanner
from intelligence_core.schema.introspector import SchemaIntrospector
from intelligence_sql.executor import QueryExecutor
from intelligence_sql.sanitizer import SQLSanitizer
from intelligence_sql.validator import SQLValidator

from app.dependencies import get_query_executor, get_query_planner, get_schema_introspector
from app.schemas import QueryRequest, QueryResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def execute_query(
    request: QueryRequest,
    introspector: SchemaIntrospector = Depends(get_schema_introspector),  # noqa: B008
    planner: QueryPlanner = Depends(get_query_planner),  # noqa: B008
    executor: QueryExecutor = Depends(get_query_executor),  # noqa: B008
):
    """Translates natural language to SQL, executes it, and returns chart specs."""
    try:
        # 1. Introspect Schema
        schema = await introspector.introspect()

        # 2. Plan Query (LLM)
        plan = await planner.plan(request.query, schema)

        # 3. Validate SQL
        validator = SQLValidator(schema)
        val_result = validator.validate(plan.sql)
        if not val_result.valid:
            raise HTTPException(
                status_code=400, detail=f"SQL Validation failed: {val_result.errors}"
            )

        # 4. Sanitize SQL
        sanitizer = SQLSanitizer()
        san_result = sanitizer.sanitize(val_result.normalized_sql)
        if not san_result.safe:
            raise HTTPException(
                status_code=400,
                detail="SQL Sanitization failed: Query contains destructive operations.",
            )

        # 5. Execute SQL
        result = await executor.execute(san_result.sanitized_sql)

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
