import logging

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.responses import StreamingResponse
from seal_core.chat.errors import SessionDatabaseMismatchError
from seal_core.chat.models import ChatMessage
from seal_core.chat.service import ChatService
from seal_core.database.registry import DatabaseRegistry

from app.database_routing import get_database_bundle, session_database_mismatch_detail
from app.dependencies import get_chat_service, get_database_registry
from app.openapi_responses import AUTH_AND_DATABASE_RESPONSES
from app.schemas import ChatRequest, ChatResponse
from app.security import require_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=None, responses=AUTH_AND_DATABASE_RESPONSES)
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
            stream = chat_service.handle_stream(
                message=request.message,
                session_id=request.session_id,
                messages_override=override,
                include_charts=request.include_charts,
                enhancement_enabled=request.enhancement,
                database_id=request.database_id,
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
    except SessionDatabaseMismatchError as exc:
        raise HTTPException(
            status_code=400,
            detail=session_database_mismatch_detail(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ChatResponse(
        session_id=result.session_id,
        message=result.message,
        sources=result.sources,
        sql=result.sql,
        results=result.results,
        columns=result.columns,
        chart=result.chart,
        metadata=result.metadata,
    )
