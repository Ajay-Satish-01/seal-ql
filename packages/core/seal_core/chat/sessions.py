"""In-memory chat session store."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from seal_core.settings import get_settings

if TYPE_CHECKING:
    from seal_core.chat.models import ChatMessage


@dataclass
class SessionState:
    messages: list[ChatMessage] = field(default_factory=list)
    summary: str | None = None
    summary_through_index: int = 0
    database_id: str | None = None
    updated_at: float = field(default_factory=time.time)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def _ttl(self) -> int:
        return get_settings().chat_session_ttl_seconds

    def _max_messages(self) -> int:
        return get_settings().chat_max_history_messages

    def _expire(self) -> None:
        now = time.time()
        expired = [sid for sid, s in self._sessions.items() if now - s.updated_at > self._ttl()]
        for sid in expired:
            del self._sessions[sid]

    def create_session(self) -> str:
        self._expire()
        sid = str(uuid.uuid4())
        self._sessions[sid] = SessionState()
        return sid

    def get_or_create(self, session_id: str | None) -> tuple[str, SessionState]:
        self._expire()
        if session_id and session_id in self._sessions:
            return session_id, self._sessions[session_id]
        sid = self.create_session()
        return sid, self._sessions[sid]

    def append(self, session_id: str, message: ChatMessage) -> None:
        _, state = self.get_or_create(session_id)
        state.messages.append(message)
        if len(state.messages) > self._max_messages():
            state.messages = state.messages[-self._max_messages() :]
        state.updated_at = time.time()
