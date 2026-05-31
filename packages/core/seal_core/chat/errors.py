"""Chat service errors."""

from __future__ import annotations

SESSION_DATABASE_ID_MISMATCH = "session_database_id_mismatch"


class SessionDatabaseMismatchError(Exception):
    """Raised when a follow-up turn uses a different database_id than the session."""

    def __init__(
        self,
        *,
        session_id: str,
        pinned_database_id: str,
        requested_database_id: str,
    ) -> None:
        self.session_id = session_id
        self.pinned_database_id = pinned_database_id
        self.requested_database_id = requested_database_id
        super().__init__(
            f"Session {session_id!r} is pinned to database_id {pinned_database_id!r}; "
            f"got {requested_database_id!r}"
        )
