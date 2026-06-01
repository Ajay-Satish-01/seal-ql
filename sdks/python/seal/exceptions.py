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


class QueryOutOfScopeError(QueryError):
    """Raised when guardrails reject a query as out of scope (HTTP 400)."""

    def __init__(
        self,
        message: str,
        *,
        reason: str = "",
        suggested_queries: list[str] | None = None,
        status_code: int | None = 400,
    ) -> None:
        super().__init__(message, status_code=status_code)
        self.reason = reason
        self.suggested_queries = list(suggested_queries or [])


class ServerError(SealError):
    """Raised when the API returns a 5xx error."""


# Deprecated alias — use SealConnectionError
ConnectionError = SealConnectionError
