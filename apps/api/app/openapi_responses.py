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
