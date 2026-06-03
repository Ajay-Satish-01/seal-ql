"""Abstract chat session store."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from seal_core.chat.session.ids import parse_session_id
from seal_core.settings import get_settings

if TYPE_CHECKING:
    from seal_core.chat.models import ChatMessage
    from seal_core.chat.session.listing import SessionListPage
    from seal_core.chat.session.models import SessionState

_TITLE_MAX_LEN = 80
_ALLOWED_ROLES = frozenset({"user", "assistant"})


class BaseSessionStore(ABC):
    """Pluggable backend for multi-turn chat session state."""

    @abstractmethod
    async def create_session(self) -> str: ...

    @abstractmethod
    async def get_or_create(self, session_id: str | None) -> tuple[str, SessionState]: ...

    @abstractmethod
    async def append(self, session_id: str, message: ChatMessage) -> None: ...

    @abstractmethod
    async def list_sessions(
        self,
        database_id: str | None = None,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> SessionListPage: ...

    @abstractmethod
    async def get_session(self, session_id: str) -> SessionState | None: ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool: ...

    async def ensure_schema(self) -> None:  # noqa: B027
        """Create backing tables when needed (Postgres). No-op by default."""

    async def close(self) -> None:
        """Release connections. No-op by default."""
        return None

    async def set_database_id(self, session_id: str, database_id: str) -> None:
        """Pin database_id after a successful in-scope turn."""
        sid = parse_session_id(session_id)
        await self._set_session_database_id(sid, database_id)

    @abstractmethod
    async def _set_session_database_id(self, session_id: str, database_id: str) -> None: ...

    def _list_limit(self, limit: int | None) -> int:
        settings = get_settings()
        cap = settings.chat_session_list_max_limit
        default = settings.chat_session_list_default_limit
        value = default if limit is None else limit
        return max(1, min(value, cap))

    @staticmethod
    def _validate_message_role(message: ChatMessage) -> None:
        if message.role not in _ALLOWED_ROLES:
            raise ValueError(f"Invalid message role: {message.role!r}")

    def _max_messages(self) -> int:
        return get_settings().chat_max_history_messages

    @staticmethod
    def _apply_title(state: SessionState, message: ChatMessage) -> None:
        if state.title is None and message.role == "user":
            state.title = message.content[:_TITLE_MAX_LEN]

    @staticmethod
    def _trim_messages(state: SessionState, max_messages: int) -> None:
        if len(state.messages) > max_messages:
            state.messages = state.messages[-max_messages:]
            state.message_timestamps = state.message_timestamps[-max_messages:]
