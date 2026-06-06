import logging

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from seal_charts.engine import ChartEngine
from seal_core.catalog.registry import DataCatalogRegistry
from seal_core.chat.retriever import ContextRetriever
from seal_core.database.config import planner_resources_for_database
from seal_core.database.registry import DatabaseRegistry
from seal_core.guardrails.models import ScopeMetadata
from seal_core.guardrails.scope import build_query_out_of_scope_detail, classify_scope
from seal_core.pipeline.execute import execute_natural_language_query
from seal_core.pipeline.models import ExecutionMetadata
from seal_core.pipeline.provenance import build_catalog_matches
from seal_core.pipeline.trust import apply_trust_gating_to_query_response
from seal_core.pipeline.validate_metadata import (
    InvalidQueryMetadataError,
    enforce_query_metadata,
)
from seal_core.planner.planner import QueryPlanner
from seal_semantic.registry import SemanticRegistry
from seal_sql.result import QueryResult

from app.database_routing import get_database_bundle
from app.dependencies import (
    get_data_catalog,
    get_database_registry,
    get_query_planner,
    get_semantic_registry,
)
from app.errors import public_query_error_detail, public_server_error_detail
from app.llm_errors import raise_for_llm_failure
from app.openapi_responses import QUERY_ENDPOINT_RESPONSES
from app.schemas import QueryRequest, QueryResponse
from app.security import require_api_key

logger = logging.getLogger(__name__)
router = APIRouter()
_context_retriever = ContextRetriever()


@router.post("/query", response_model=QueryResponse, responses=QUERY_ENDPOINT_RESPONSES)
async def execute_query(
    request: QueryRequest,
    _: None = Security(require_api_key),
    registry: DatabaseRegistry = Depends(get_database_registry),  # noqa: B008
    planner: QueryPlanner = Depends(get_query_planner),  # noqa: B008
    semantic_registry: SemanticRegistry = Depends(get_semantic_registry),  # noqa: B008
    data_catalog: DataCatalogRegistry = Depends(get_data_catalog),  # noqa: B008
):
    """Translates natural language to SQL, executes it, and returns chart specs."""
    try:
        bundle = get_database_bundle(registry, request.database_id)

        scope = await classify_scope(request.query, channel="query")
        if not scope.in_scope:
            raise HTTPException(
                status_code=400,
                detail=build_query_out_of_scope_detail(scope),
            )

        schema = await bundle.introspector.introspect()
        semantic, catalog = planner_resources_for_database(
            request.database_id,
            catalog=data_catalog,
            semantic_registry=semantic_registry,
        )

        table_names = _context_retriever.select_tables(
            request.query,
            schema,
            catalog,
            full_schema=True,
        )

        exec_result = await execute_natural_language_query(
            question=request.query,
            schema=schema,
            planner=planner,
            executor=bundle.executor,
            semantic_registry=semantic,
            data_catalog=catalog,
            table_names=None,
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

        catalog_matches = build_catalog_matches(table_names, schema, catalog)
        metadata = ExecutionMetadata.from_execute_result(
            database_id=request.database_id,
            exec_result=exec_result,
            used_sql=True,
            catalog_matches=catalog_matches,
        ).model_dump()
        metadata["scope"] = ScopeMetadata.from_result(scope).model_dump(exclude_none=True)
        enforce_query_metadata(metadata)

        response_model = QueryResponse(
            sql=exec_result.sql,
            columns=exec_result.columns,
            results=exec_result.rows,
            chart=chart_spec,
            sources=table_names,
            metadata=metadata,
        )
        response_payload = apply_trust_gating_to_query_response(response_model.model_dump())
        return JSONResponse(content=jsonable_encoder(response_payload))
    except HTTPException:
        raise
    except InvalidQueryMetadataError as e:
        logger.error("Query metadata validation failed: %s", e.errors)
        raise HTTPException(status_code=500, detail=public_server_error_detail()) from e
    except Exception as e:
        if "Validation" in str(e) or "Sanitization" in str(e):
            logger.error("Query failed: %s", e)
            raise HTTPException(status_code=400, detail=public_query_error_detail()) from e
        try:
            raise_for_llm_failure(e)
        except HTTPException:
            raise
        logger.exception("Failed to execute query")
        raise HTTPException(status_code=500, detail=public_server_error_detail()) from e
