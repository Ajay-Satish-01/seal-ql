"""Resolve database_id to a configured DatabaseBundle."""

from __future__ import annotations

from fastapi import HTTPException
from seal_core.chat.errors import SESSION_DATABASE_ID_MISMATCH, SessionDatabaseMismatchError
from seal_core.database.registry import DatabaseBundle, DatabaseRegistry, UnknownDatabaseError


def get_database_bundle(registry: DatabaseRegistry, database_id: str) -> DatabaseBundle:
    """Return the bundle for database_id or raise HTTP 404."""
    try:
        return registry.get(database_id)
    except UnknownDatabaseError as exc:
        raise HTTPException(status_code=404, detail="unknown_database_id") from exc


def session_database_mismatch_detail(exc: SessionDatabaseMismatchError) -> dict[str, str]:
    """Structured FastAPI detail for a pinned-session database_id mismatch."""
    return {
        "code": SESSION_DATABASE_ID_MISMATCH,
        "message": str(exc),
        "session_id": exc.session_id,
        "pinned_database_id": exc.pinned_database_id,
        "requested_database_id": exc.requested_database_id,
    }
