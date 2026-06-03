"""Session id parsing shared by stores and API routes."""

from __future__ import annotations

import uuid


class InvalidSessionIdError(ValueError):
    """Raised when a client-provided session id is not a valid UUID."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Invalid session_id: {session_id!r}")


def parse_session_id(session_id: str) -> str:
    """Normalize to canonical UUID string; raise :class:`InvalidSessionIdError` if invalid."""
    try:
        return str(uuid.UUID(session_id))
    except ValueError as exc:
        raise InvalidSessionIdError(session_id) from exc
