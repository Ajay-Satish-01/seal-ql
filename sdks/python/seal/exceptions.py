"""Seal Python SDK — exceptions."""

from __future__ import annotations


class SealError(Exception):
    """Base exception for all SDK errors."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class SealConnectionError(SealError):
    """Raised when the SDK cannot reach the API server."""


class QueryError(SealError):
    """Raised when the API rejects a query (validation, sanitization, or execution failure)."""


class ServerError(SealError):
    """Raised when the API returns a 5xx error."""


# Deprecated alias — use SealConnectionError
ConnectionError = SealConnectionError
