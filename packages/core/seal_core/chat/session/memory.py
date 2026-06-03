"""In-memory chat session store (single-process only)."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import TYPE_CHECKING

from seal_core.chat.session.base import BaseSessionStore
from seal_core.chat.session.ids import parse_session_id
from seal_core.chat.session.listing import (
    SessionListPage,
    matches_database_filter,
    paginate_summaries,
)
from seal_core.chat.session.models import SessionState, SessionSummary
from seal_core.settings import get_settings

if TYPE_CHECKING:
    from seal_core.chat.models import ChatMessage


class InMemorySessionStore(BaseSessionStore):
    """Ephemeral sessions for local Docker / single API process.

    Does NOT survive Lambda cold starts or multi-task ECS without sticky sessions.
    Use CHAT_SESSION_STORE=postgres for shared persistent history.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = asyncio.Lock()

    def _ttl(self) -> int:
        return get_settings().chat_session_ttl_seconds

    def _expire(self) -> None:
        now = time.time()
        expired = [sid for sid, s in self._sessions.items() if now - s.updated_at > self._ttl()]
        for sid in expired:
            del self._sessions[sid]

    async def create_session(self) -> str:
        return str(uuid.uuid4())

    async def get_or_create(self, session_id: str | None) -> tuple[str, SessionState]:
        async with self._lock:
            self._expire()
            sid = parse_session_id(session_id) if session_id is not None else str(uuid.uuid4())
            if sid not in self._sessions:
                self._sessions[sid] = SessionState()
            return sid, self._sessions[sid]

    async def append(self, session_id: str, message: ChatMessage) -> None:
        self._validate_message_role(message)
        sid = parse_session_id(session_id)
        async with self._lock:
            self._expire()
            if sid not in self._sessions:
                self._sessions[sid] = SessionState()
            state = self._sessions[sid]
            state.messages.append(message)
            state.message_timestamps.append(None)
            self._apply_title(state, message)
            self._trim_messages(state, self._max_messages())
            state.updated_at = time.time()

    async def list_sessions(
        self,
        database_id: str | None = None,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> SessionListPage:
        page_size = self._list_limit(limit)
        async with self._lock:
            self._expire()
            summaries: list[SessionSummary] = []
            for sid, state in self._sessions.items():
                if not state.messages:
                    continue
                if not matches_database_filter(state.database_id, database_id):
                    continue
                summaries.append(
                    SessionSummary(
                        session_id=sid,
                        title=state.title,
                        database_id=state.database_id,
                        message_count=len(state.messages),
                        created_at=state.created_at,
                        updated_at=state.updated_at,
                    )
                )
        sessions, has_more = paginate_summaries(summaries, limit=page_size, offset=offset)
        return SessionListPage(sessions=sessions, has_more=has_more)

    async def get_session(self, session_id: str) -> SessionState | None:
        sid = parse_session_id(session_id)
        async with self._lock:
            self._expire()
            state = self._sessions.get(sid)
            if state is None:
                return None
            return SessionState(
                messages=list(state.messages),
                message_timestamps=list(state.message_timestamps),
                summary=state.summary,
                summary_through_index=state.summary_through_index,
                database_id=state.database_id,
                title=state.title,
                created_at=state.created_at,
                updated_at=state.updated_at,
            )

    async def delete_session(self, session_id: str) -> bool:
        sid = parse_session_id(session_id)
        async with self._lock:
            self._expire()
            if sid not in self._sessions:
                return False
            del self._sessions[sid]
            return True

    async def _set_session_database_id(self, session_id: str, database_id: str) -> None:
        async with self._lock:
            state = self._sessions.get(session_id)
            if state is not None and state.database_id is None:
                state.database_id = database_id
