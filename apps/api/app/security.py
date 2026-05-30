"""API key authentication for Seal (FastAPI / Starlette security utilities)."""

from __future__ import annotations

import logging
import secrets

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from seal_core.settings import Settings, get_settings

logger = logging.getLogger(__name__)

API_KEY_HEADER_NAME = "X-API-Key"

# Official FastAPI security primitive — timing-safe compare via secrets.compare_digest.
API_KEY_HEADER = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)

_AUTH_MISCONFIGURED_DETAIL = "API authentication is misconfigured"
_AUTH_INVALID_DETAIL = "Invalid or missing API key"


def is_api_auth_enabled(settings: Settings | None = None) -> bool:
    """Return True when ``SEAL_API_KEY`` is set to a non-empty value."""
    resolved = settings if settings is not None else get_settings()
    return bool(resolved.api_key)


async def require_api_key(
    request: Request,
    api_key: str | None = Security(API_KEY_HEADER),
) -> None:
    """Require a valid API key on protected routes when ``SEAL_API_KEY`` is configured."""
    settings = get_settings()

    if settings.auth_required and not is_api_auth_enabled(settings):
        logger.error("SEAL_AUTH_REQUIRED is enabled but SEAL_API_KEY is not set")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_AUTH_MISCONFIGURED_DETAIL,
        )

    if not is_api_auth_enabled(settings):
        return

    if not _api_key_matches(api_key, settings.api_key):
        client_host = request.client.host if request.client else "unknown"
        logger.warning(
            "API key authentication failed for a protected route (client=%s)",
            client_host,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_AUTH_INVALID_DETAIL,
        )


def _api_key_matches(provided: str | None, expected: str | None) -> bool:
    """Constant-time comparison that is safe for arbitrary (non-ASCII) header values."""
    if not provided or not expected:
        return False
    # Compare bytes: secrets.compare_digest raises TypeError on non-ASCII str input.
    return secrets.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))
