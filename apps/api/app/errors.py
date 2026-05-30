"""Safe HTTP error messages — never leak SQL, schema, or LLM internals to clients."""

from __future__ import annotations

QUERY_FAILED_MESSAGE = "Query failed. See server logs for details."
INTERNAL_ERROR_MESSAGE = "An internal error occurred."


def public_query_error_detail() -> str:
    return QUERY_FAILED_MESSAGE


def public_server_error_detail() -> str:
    return INTERNAL_ERROR_MESSAGE
