import logging

from fastapi import APIRouter, Depends, HTTPException, Security
from seal_charts.engine import ChartEngine
from seal_core.catalog.registry import DataCatalogRegistry
from seal_core.pipeline.execute import execute_natural_language_query
from seal_core.planner.planner import QueryPlanner
from seal_core.schema.introspector import SchemaIntrospector
from seal_semantic.registry import SemanticRegistry
from seal_sql.executor import QueryExecutor
from seal_sql.result import QueryResult

from app.dependencies import (
    get_data_catalog,
    get_query_executor,
    get_query_planner,
    get_schema_introspector,
    get_semantic_registry,
)
from app.errors import public_query_error_detail, public_server_error_detail
from app.openapi_responses import UNAUTHORIZED_RESPONSE
from app.schemas import QueryRequest, QueryResponse
from app.security import require_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query", response_model=QueryResponse, responses=UNAUTHORIZED_RESPONSE)
async def execute_query(
    request: QueryRequest,
    _: None = Security(require_api_key),
    introspector: SchemaIntrospector = Depends(get_schema_introspector),  # noqa: B008
    planner: QueryPlanner = Depends(get_query_planner),  # noqa: B008
    executor: QueryExecutor = Depends(get_query_executor),  # noqa: B008
    semantic_registry: SemanticRegistry = Depends(get_semantic_registry),  # noqa: B008
    data_catalog: DataCatalogRegistry = Depends(get_data_catalog),  # noqa: B008
):
    """Translates natural language to SQL, executes it, and returns chart specs."""
    try:
        schema = await introspector.introspect()

        exec_result = await execute_natural_language_query(
            question=request.query,
            schema=schema,
            planner=planner,
            executor=executor,
            semantic_registry=semantic_registry,
            data_catalog=data_catalog,
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

        return QueryResponse(
            sql=exec_result.sql,
            columns=exec_result.columns,
            results=exec_result.rows,
            chart=chart_spec,
            metadata={
                "row_count": exec_result.row_count,
                "execution_time_ms": exec_result.execution_time_ms,
                "truncated": exec_result.truncated,
                "warnings": exec_result.warnings,
                "repair_attempts": exec_result.repair_attempts,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        if "Validation" in str(e) or "Sanitization" in str(e):
            logger.error("Query failed: %s", e)
            raise HTTPException(status_code=400, detail=public_query_error_detail()) from e
        logger.exception("Failed to execute query")
        raise HTTPException(status_code=500, detail=public_server_error_detail()) from e
