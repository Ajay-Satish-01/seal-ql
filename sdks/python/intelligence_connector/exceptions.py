"""Intelligence Connector Python SDK — exceptions."""

from __future__ import annotations


class IntelligenceConnectorError(Exception):
    """Base exception for all SDK errors."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ConnectionError(IntelligenceConnectorError):
    """Raised when the SDK cannot reach the API server."""


class QueryError(IntelligenceConnectorError):
    """Raised when the API rejects a query (validation, sanitization, or execution failure)."""


class ServerError(IntelligenceConnectorError):
    """Raised when the API returns a 5xx error."""
