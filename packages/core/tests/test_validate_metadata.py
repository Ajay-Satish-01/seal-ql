"""Tests for metadata validation helpers."""

from __future__ import annotations

from seal_core.pipeline.models import build_stream_meta_event
from seal_core.pipeline.validate_metadata import (
    validate_enhancement_block,
    validate_nested_chat_metadata,
    validate_query_metadata,
    validate_stream_meta_event,
)


def test_validate_query_metadata_requires_execution_and_used_sql() -> None:
    errors = validate_query_metadata({"database_id": "default", "used_sql": True})
    assert any("execution keys" in e for e in errors)

    ok = validate_query_metadata(
        {
            "database_id": "default",
            "row_count": 1,
            "execution_time_ms": 1.0,
            "truncated": False,
            "warnings": [],
            "repair_attempts": 0,
            "used_sql": True,
        }
    )
    assert not ok


def test_validate_stream_meta_event_accepts_built_payload() -> None:
    event = build_stream_meta_event(
        session_id="s1",
        database_id="default",
        exec_result=None,
        used_sql=False,
        enhancement_enabled=False,
        applied=[],
        sources=[],
        sql=None,
        results=None,
        columns=None,
        chart=None,
        scope=None,
        vector_rag_available=False,
        orchestrator_available=True,
    )
    assert not validate_stream_meta_event(event)


def test_validate_stream_meta_event_requires_execution_when_sql_present() -> None:
    errors = validate_stream_meta_event(
        {
            "session_id": "s1",
            "sql": "SELECT 1",
            "enhancement": {"enabled": True, "applied": []},
            "used_sql": True,
        }
    )
    assert any("execution keys" in e for e in errors)


def test_validate_stream_meta_event_rejects_empty_session_id() -> None:
    errors = validate_stream_meta_event(
        {
            "session_id": "",
            "used_sql": False,
            "enhancement": {"enabled": False, "applied": []},
        }
    )
    assert any("session_id" in e for e in errors)


def test_validate_nested_chat_metadata_requires_enhancement_on_sql_error() -> None:
    errors = validate_nested_chat_metadata(
        {
            "used_sql": False,
            "sql_error": True,
            "database_id": "default",
            "row_count": 0,
            "execution_time_ms": 0,
            "truncated": False,
            "warnings": [],
            "repair_attempts": 0,
        },
        sql_at_top_level=False,
    )
    assert any("enhancement" in e for e in errors)


def test_validate_enhancement_block_rejects_non_boolean_enabled() -> None:
    errors = validate_enhancement_block(
        {"enabled": "true", "applied": []},
        required=True,
    )
    assert any("enabled must be a boolean" in e for e in errors)


def test_validate_nested_chat_metadata_sql_error_with_enhancement_ok() -> None:
    errors = validate_nested_chat_metadata(
        {
            "used_sql": False,
            "sql_error": True,
            "enhancement": {"enabled": True, "applied": []},
            "database_id": "default",
            "row_count": 0,
            "execution_time_ms": 0,
            "truncated": False,
            "warnings": [],
            "repair_attempts": 0,
        },
        sql_at_top_level=False,
    )
    assert not errors
