"""Parse FastAPI error bodies into SDK exceptions."""

from __future__ import annotations

from typing import Any

from seal.exceptions import QueryError, QueryOutOfScopeError, ServerError
from seal.rate_limit import is_rate_limit_http, rate_limit_user_message

_SESSION_DATABASE_ID_MISMATCH = "session_database_id_mismatch"

RATE_LIMIT_USER_MESSAGE = rate_limit_user_message()


def is_rate_limit_signal(status: int, text: str) -> bool:
    """True when an HTTP status or message body indicates LLM rate limiting."""
    return is_rate_limit_http(status, text)


def _format_out_of_scope_message(*, reason: str, suggested_queries: list[str]) -> str:
    message = f"Query out of scope ({reason})" if reason else "Query out of scope"
    if suggested_queries:
        examples = " · ".join(f'"{q}"' for q in suggested_queries)
        message = f"{message}. Try: {examples}"
    return message


def _parse_suggested_queries(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    cleaned: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            cleaned.append(item.strip()[:200])
        if len(cleaned) >= 3:
            break
    return cleaned


def _validation_item_message(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in ("msg", "message", "detail"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return str(item).strip()


def detail_to_message(detail: Any) -> str:
    """Human-readable message from a FastAPI ``detail`` field (string or object)."""
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        parts = [_validation_item_message(item) for item in detail]
        joined = "; ".join(part for part in parts if part)
        return joined or str(detail)
    if isinstance(detail, dict):
        message = detail.get("message")
        if isinstance(message, str) and message.strip():
            return message
        if detail.get("detail") == "query_out_of_scope":
            reason = str(detail.get("reason") or "")
            suggested = _parse_suggested_queries(detail.get("suggested_queries"))
            return _format_out_of_scope_message(reason=reason, suggested_queries=suggested)
        code = detail.get("code")
        if code == _SESSION_DATABASE_ID_MISMATCH:
            pinned = detail.get("pinned_database_id", "?")
            requested = detail.get("requested_database_id", "?")
            return (
                f"Session is pinned to database {pinned!r} but request used {requested!r}. "
                "Start a new chat session or use the pinned database."
            )
        if isinstance(code, str):
            return code
    return str(detail)


def raise_for_response(response_status: int, detail: Any) -> None:
    """Raise an appropriate SDK exception for a non-2xx HTTP response."""
    if response_status >= 500:
        message = detail_to_message(detail)
        user_message = (
            RATE_LIMIT_USER_MESSAGE if is_rate_limit_signal(response_status, message) else message
        )
        raise ServerError(
            f"Server error ({response_status}): {user_message}",
            status_code=response_status,
        )

    if response_status >= 400:
        if isinstance(detail, dict) and detail.get("detail") == "query_out_of_scope":
            reason = str(detail.get("reason") or "")
            suggested = _parse_suggested_queries(detail.get("suggested_queries"))
            message = _format_out_of_scope_message(reason=reason, suggested_queries=suggested)
            raise QueryOutOfScopeError(
                message,
                reason=reason,
                suggested_queries=suggested,
                status_code=response_status,
            )
        message = detail_to_message(detail)
        raise QueryError(
            f"Query rejected ({response_status}): {message}",
            status_code=response_status,
        )
