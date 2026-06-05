import logging

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from seal_core.chat.errors import SessionDatabaseMismatchError
from seal_core.chat.models import ChatMessage
from seal_core.chat.service import ChatService
from seal_core.chat.session.ids import InvalidSessionIdError
from seal_core.database.registry import DatabaseRegistry
from seal_core.pipeline.trust import apply_trust_gating_to_chat_response

from app.database_routing import get_database_bundle, session_database_mismatch_detail
from app.dependencies import get_chat_service, get_database_registry
from app.errors import public_server_error_detail
from app.llm_errors import raise_for_llm_failure
from app.openapi_responses import CHAT_ENDPOINT_RESPONSES
from app.schemas import ChatRequest, ChatResponse
from app.security import require_api_key
from app.session_http import raise_session_not_found

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses=CHAT_ENDPOINT_RESPONSES,
)
async def chat(
    request: ChatRequest,
    _: None = Security(require_api_key),
    chat_service: ChatService = Depends(get_chat_service),  # noqa: B008
    registry: DatabaseRegistry = Depends(get_database_registry),  # noqa: B008
):
    """Schema-grounded conversational Q&A with optional charts and streaming."""
    get_database_bundle(registry, request.database_id)
    override = None
    if request.messages:
        for m in request.messages:
            if m.role.strip().lower() == "system":
                raise HTTPException(
                    status_code=400,
                    detail="system role is not allowed in messages override",
                )
        override = [ChatMessage(role=m.role, content=m.content) for m in request.messages]

    try:
        if request.stream:
            ctx = await chat_service.prepare_stream_turn(
                message=request.message,
                session_id=request.session_id,
                messages_override=override,
                enhancement_enabled=request.enhancement,
                database_id=request.database_id,
            )
            stream = chat_service.stream_turn(
                ctx,
                message=request.message,
                include_charts=request.include_charts,
            )
            return StreamingResponse(stream, media_type="text/event-stream")

        result = await chat_service.handle_json(
            message=request.message,
            session_id=request.session_id,
            messages_override=override,
            include_charts=request.include_charts,
            enhancement_enabled=request.enhancement,
            database_id=request.database_id,
        )
    except InvalidSessionIdError as exc:
        raise_session_not_found(exc)
    except SessionDatabaseMismatchError as exc:
        raise HTTPException(
            status_code=400,
            detail=session_database_mismatch_detail(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        try:
            raise_for_llm_failure(exc)
        except HTTPException:
            raise
        logger.exception("Chat request failed")
        raise HTTPException(status_code=500, detail=public_server_error_detail()) from exc

    response_payload = apply_trust_gating_to_chat_response(
        {
            "session_id": result.session_id,
            "message": result.message,
            "sources": result.sources,
            "sql": result.sql,
            "results": result.results,
            "columns": result.columns,
            "chart": (
                result.chart.model_dump() if hasattr(result.chart, "model_dump") else result.chart
            ),
            "metadata": result.metadata,
        }
    )
    return JSONResponse(content=jsonable_encoder(response_payload))
