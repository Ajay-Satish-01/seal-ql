import logging

from fastapi import APIRouter, Depends, Security
from fastapi.responses import StreamingResponse
from seal_core.chat.models import ChatMessage
from seal_core.chat.service import ChatService
from seal_core.schema.introspector import SchemaIntrospector

from app.dependencies import get_chat_service, get_schema_introspector
from app.openapi_responses import UNAUTHORIZED_RESPONSE
from app.schemas import ChatRequest, ChatResponse
from app.security import require_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=None, responses=UNAUTHORIZED_RESPONSE)
async def chat(
    request: ChatRequest,
    _: None = Security(require_api_key),
    chat_service: ChatService = Depends(get_chat_service),  # noqa: B008
    introspector: SchemaIntrospector = Depends(get_schema_introspector),  # noqa: B008
):
    """Schema-grounded conversational Q&A with optional charts and streaming."""
    schema = await introspector.introspect()
    override = None
    if request.messages:
        override = [ChatMessage(role=m.role, content=m.content) for m in request.messages]

    if request.stream:

        async def event_stream():
            async for chunk in chat_service.handle_stream(
                message=request.message,
                session_id=request.session_id,
                messages_override=override,
                include_charts=request.include_charts,
                enhancement_enabled=request.enhancement,
                schema=schema,
            ):
                yield chunk

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    result = await chat_service.handle_json(
        message=request.message,
        session_id=request.session_id,
        messages_override=override,
        include_charts=request.include_charts,
        enhancement_enabled=request.enhancement,
        schema=schema,
    )

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
