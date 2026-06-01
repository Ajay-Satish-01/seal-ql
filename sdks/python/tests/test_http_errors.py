"""Tests for FastAPI error body parsing in the Python SDK."""

from __future__ import annotations

import pytest
from seal._http_errors import detail_to_message, raise_for_response
from seal.exceptions import QueryError, QueryOutOfScopeError


def test_detail_to_message_session_database_mismatch() -> None:
    msg = detail_to_message(
        {
            "code": "session_database_id_mismatch",
            "message": "Session 's1' is pinned to database_id 'default'; got 'analytics'",
            "session_id": "s1",
            "pinned_database_id": "default",
            "requested_database_id": "analytics",
        }
    )
    assert "pinned" in msg.lower()
    assert "analytics" in msg


def test_raise_for_response_query_out_of_scope() -> None:
    with pytest.raises(QueryOutOfScopeError) as exc_info:
        raise_for_response(
            400,
            {
                "detail": "query_out_of_scope",
                "reason": "off-topic",
                "suggested_queries": ["Show order count by month"],
            },
        )
    assert exc_info.value.suggested_queries == ["Show order count by month"]


def test_detail_to_message_fastapi_422_list() -> None:
    msg = detail_to_message(
        [
            {"type": "missing", "loc": ["body", "query"], "msg": "Field required"},
            {"type": "string_too_long", "loc": ["body", "query"], "msg": "Too long"},
        ]
    )
    assert msg == "Field required; Too long"


def test_raise_for_response_structured_chat_error_uses_message() -> None:
    with pytest.raises(QueryError, match="pinned to database_id"):
        raise_for_response(
            400,
            {
                "code": "session_database_id_mismatch",
                "message": "Session 's1' is pinned to database_id 'default'; got 'analytics'",
            },
        )
