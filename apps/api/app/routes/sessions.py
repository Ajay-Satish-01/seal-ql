"""Chat session history routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from seal_core.chat.session.ids import InvalidSessionIdError, parse_session_id

if TYPE_CHECKING:
    from seal_core.chat.session.base import BaseSessionStore

from app.dependencies import get_session_store
from app.schemas import (
    SessionDetailResponse,
    SessionListResponse,
    SessionMessageSchema,
    SessionSummarySchema,
)
from app.security import require_api_key
from app.session_http import raise_session_not_found

router = APIRouter()


def _iso_timestamp(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()


@router.get("/chat/sessions", response_model=SessionListResponse)
async def list_chat_sessions(
    database_id: str | None = Query(None, description="Filter by pinned database_id."),
    limit: int | None = Query(
        None,
        ge=1,
        description="Page size (default from CHAT_SESSION_LIST_DEFAULT_LIMIT).",
    ),
    offset: int = Query(0, ge=0, description="Pagination offset."),
    _: None = Security(require_api_key),
    store: BaseSessionStore = Depends(get_session_store),  # noqa: B008
) -> SessionListResponse:
    """List chat sessions with messages (most recent first).

    Sessions are global to the API key (single-tenant ops dashboard).
    Limit is clamped by the store to ``CHAT_SESSION_LIST_MAX_LIMIT``.
    """
    page = await store.list_sessions(
        database_id=database_id,
        limit=limit,
        offset=offset,
    )
    return SessionListResponse(
        sessions=[
            SessionSummarySchema(
                session_id=s.session_id,
                title=s.title,
                database_id=s.database_id,
                message_count=s.message_count,
                created_at=_iso_timestamp(s.created_at),
                updated_at=_iso_timestamp(s.updated_at),
            )
            for s in page.sessions
        ],
        has_more=page.has_more,
    )


@router.get("/chat/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_chat_session(
    session_id: str,
    _: None = Security(require_api_key),
    store: BaseSessionStore = Depends(get_session_store),  # noqa: B008
) -> SessionDetailResponse:
    """Load full message history for a session."""
    try:
        sid = parse_session_id(session_id)
    except InvalidSessionIdError as exc:
        raise_session_not_found(exc)
    state = await store.get_session(sid)
    if state is None:
        raise HTTPException(status_code=404, detail="session_not_found")
    timestamps = state.message_timestamps
    return SessionDetailResponse(
        session_id=sid,
        title=state.title,
        database_id=state.database_id,
        messages=[
            SessionMessageSchema(
                role=m.role,
                content=m.content,
                created_at=(
                    _iso_timestamp(timestamps[i])
                    if i < len(timestamps) and timestamps[i] is not None
                    else None
                ),
            )
            for i, m in enumerate(state.messages)
        ],
        created_at=_iso_timestamp(state.created_at),
        updated_at=_iso_timestamp(state.updated_at),
    )


@router.delete("/chat/sessions/{session_id}", status_code=204)
async def delete_chat_session(
    session_id: str,
    _: None = Security(require_api_key),
    store: BaseSessionStore = Depends(get_session_store),  # noqa: B008
) -> None:
    """Delete a chat session and its messages."""
    try:
        sid = parse_session_id(session_id)
    except InvalidSessionIdError as exc:
        raise_session_not_found(exc)
    deleted = await store.delete_session(sid)
    if not deleted:
        raise HTTPException(status_code=404, detail="session_not_found")
