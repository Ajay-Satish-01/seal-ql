import logging

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from seal_core.database.registry import DatabaseRegistry, UnknownDatabaseError
from seal_core.guardrails.scope import build_query_out_of_scope_detail
from seal_core.pipeline.query_service import QueryOutOfScopeError, QueryService
from seal_core.pipeline.trust import apply_trust_gating_to_query_response
from seal_core.pipeline.validate_metadata import InvalidQueryMetadataError
from seal_sql.boundary import is_boundary_error_message

from app.database_routing import get_database_bundle
from app.dependencies import get_database_registry, get_query_service
from app.errors import public_query_error_detail, public_server_error_detail
from app.llm_errors import raise_for_llm_failure
from app.openapi_responses import QUERY_ENDPOINT_RESPONSES
from app.schemas import QueryRequest, QueryResponse
from app.security import require_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query", response_model=QueryResponse, responses=QUERY_ENDPOINT_RESPONSES)
async def execute_query(
    request: QueryRequest,
    _: None = Security(require_api_key),
    query_service: QueryService = Depends(get_query_service),  # noqa: B008
    registry: DatabaseRegistry = Depends(get_database_registry),  # noqa: B008
):
    """Translates natural language to SQL, executes it, and returns chart specs."""
    get_database_bundle(registry, request.database_id)
    try:
        result = await query_service.execute(
            query=request.query,
            database_id=request.database_id,
        )
    except UnknownDatabaseError as exc:
        raise HTTPException(status_code=404, detail="unknown_database_id") from exc
    except QueryOutOfScopeError as exc:
        raise HTTPException(
            status_code=400,
            detail=build_query_out_of_scope_detail(exc.scope),
        ) from exc
    except InvalidQueryMetadataError as exc:
        logger.error("Query metadata validation failed: %s", exc.errors)
        raise HTTPException(status_code=500, detail=public_server_error_detail()) from exc
    except HTTPException:
        raise
    except Exception as exc:
        if is_boundary_error_message(str(exc)):
            logger.error("Query failed: %s", exc)
            raise HTTPException(status_code=400, detail=public_query_error_detail()) from exc
        try:
            raise_for_llm_failure(exc)
        except HTTPException:
            raise
        logger.exception("Failed to execute query")
        raise HTTPException(status_code=500, detail=public_server_error_detail()) from exc

    response_model = QueryResponse(
        message=result.message,
        sql=result.sql,
        columns=result.columns,
        results=result.results,
        chart=result.chart,
        sources=result.sources,
        metadata=result.metadata,
    )
    response_payload = apply_trust_gating_to_query_response(response_model.model_dump())
    return JSONResponse(content=jsonable_encoder(response_payload))
