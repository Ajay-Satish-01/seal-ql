"""Shared OpenAPI response definitions."""

from __future__ import annotations

UNAUTHORIZED_RESPONSE: dict[int, dict[str, object]] = {
    401: {
        "description": "Invalid or missing API key",
        "content": {
            "application/json": {
                "example": {"detail": "Invalid or missing API key"},
            }
        },
    }
}

UNKNOWN_DATABASE_RESPONSE: dict[int, dict[str, object]] = {
    404: {
        "description": "Unknown database_id",
        "content": {
            "application/json": {
                "example": {"detail": "unknown_database_id"},
            }
        },
    }
}

AUTH_AND_DATABASE_RESPONSES: dict[int, dict[str, object]] = {
    **UNAUTHORIZED_RESPONSE,
    **UNKNOWN_DATABASE_RESPONSE,
}
