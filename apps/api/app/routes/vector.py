"""Vector index management routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Security
from pydantic import BaseModel
from seal_core.vector.indexer import VectorIndexBuilder

from app.dependencies import get_data_catalog, get_schema_introspector
from app.errors import public_server_error_detail
from app.llm_errors import raise_for_llm_failure
from app.openapi_responses import UNAUTHORIZED_RESPONSE
from app.security import require_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


class VectorReindexResponse(BaseModel):
    status: str
    indexed_tables: int


@router.post(
    "/vector/reindex",
    response_model=VectorReindexResponse,
    responses=UNAUTHORIZED_RESPONSE,
)
async def reindex_vector(
    request: Request,
    _: None = Security(require_api_key),
    introspector=Depends(get_schema_introspector),  # noqa: B008
    catalog=Depends(get_data_catalog),  # noqa: B008
):
    store = getattr(request.app.state, "vector_store", None)
    if store is None:
        raise HTTPException(status_code=400, detail="Vector store is not configured.")
    try:
        schema = await introspector.introspect()
        builder = VectorIndexBuilder(store)
        await builder.build(schema, catalog)
    except HTTPException:
        raise
    except Exception as exc:
        try:
            raise_for_llm_failure(exc)
        except HTTPException:
            raise
        logger.exception("Vector reindex failed")
        raise HTTPException(status_code=500, detail=public_server_error_detail()) from exc
    return VectorReindexResponse(status="ok", indexed_tables=len(schema.tables))
