"""Tests for QueryResponse and demo fixture validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "packages" / "core"))

from response_validation import (  # noqa: E402
    validate_chat_response,
    validate_chat_stream_meta,
    validate_query_response,
)
from seal_core.pipeline.validate_metadata import chat_response_to_stream_meta  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_PATH = ROOT / "apps" / "docs" / "src" / "data" / "demo-fixtures.json"


@pytest.fixture
def fixtures_data() -> dict:
    with FIXTURES_PATH.open() as f:
        return json.load(f)


def test_all_demo_presets_validate(fixtures_data: dict) -> None:
    for preset in fixtures_data["presets"]:
        errors = validate_query_response(preset["response"])
        assert not errors, f"preset {preset['id']}: {errors}"


def test_vega_presets_have_encodings(fixtures_data: dict) -> None:
    vega_types = {"bar", "line", "pie", "scatter", "area"}
    for preset in fixtures_data["presets"]:
        chart = preset["response"]["chart"]
        if chart["chart_type"] not in vega_types:
            continue
        spec = chart["vega_lite_spec"]
        assert spec.get("$schema")
        enc = spec.get("encoding", {})
        if chart["chart_type"] == "pie":
            assert "theta" in enc and "color" in enc
        else:
            assert "x" in enc and "y" in enc


def _query_metadata(**overrides: object) -> dict:
    base = {
        "database_id": "default",
        "row_count": 0,
        "execution_time_ms": 1.0,
        "truncated": False,
        "warnings": [],
        "repair_attempts": 0,
        "used_sql": True,
    }
    base.update(overrides)
    return base


def test_null_chart_allowed() -> None:
    payload = {
        "sql": "SELECT 1",
        "columns": [{"name": "x", "type": "int"}],
        "results": [],
        "chart": None,
        "metadata": _query_metadata(),
    }
    assert not validate_query_response(payload)


def test_metric_card_empty_vega() -> None:
    payload = {
        "sql": "SELECT COUNT(*) AS n FROM t",
        "columns": [{"name": "n", "type": "int8"}],
        "results": [{"n": 1}],
        "chart": {
            "chart_type": "metric_card",
            "vega_lite_spec": {},
            "metadata": {"y_field": "n"},
        },
        "metadata": _query_metadata(row_count=1),
    }
    assert not validate_query_response(payload)


def test_chat_refusal_with_suggested_queries_validates() -> None:
    payload = {
        "session_id": "s-refusal",
        "message": "I only answer data questions.",
        "metadata": {
            "database_id": "default",
            "row_count": 0,
            "execution_time_ms": 0,
            "truncated": False,
            "warnings": [],
            "repair_attempts": 0,
            "used_sql": False,
            "enhancement": {"enabled": False, "applied": []},
            "scope": {"in_scope": False, "reason": "off-topic", "source": "heuristic"},
            "refusal": True,
            "suggested_queries": [
                "Show order count by month",
                "What tables are available?",
            ],
        },
    }
    assert not validate_chat_response(payload)


def test_chat_response_with_sql_metadata_validates() -> None:
    payload = {
        "session_id": "s1",
        "message": "Here are the results.",
        "sql": "SELECT 1",
        "columns": [{"name": "id", "type": "int"}],
        "results": [{"id": 1}],
        "metadata": {
            "database_id": "default",
            "row_count": 1,
            "execution_time_ms": 1.0,
            "truncated": False,
            "warnings": [],
            "repair_attempts": 0,
            "used_sql": True,
            "enhancement": {"enabled": False, "applied": []},
        },
    }
    assert not validate_chat_response(payload)


def test_query_response_missing_execution_metadata_fails() -> None:
    payload = {
        "sql": "SELECT 1",
        "columns": [{"name": "x", "type": "int"}],
        "results": [{"x": 1}],
        "metadata": {"row_count": 1},
    }
    errors = validate_query_response(payload)
    assert any("execution keys" in e for e in errors)


def test_chat_stream_meta_validates_built_event() -> None:
    from seal_core.pipeline.models import build_stream_meta_event

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
    assert not validate_chat_stream_meta(event)


def test_chat_response_missing_execution_metadata_fails() -> None:
    payload = {
        "session_id": "s1",
        "message": "Results",
        "sql": "SELECT 1",
        "metadata": {"used_sql": True},
    }
    errors = validate_chat_response(payload)
    assert any("execution keys" in e for e in errors)


def _demo_chat_response_from_preset(preset: dict) -> dict:
    """Mirror apps/docs demo-chat-fixtures chatResponseFromPreset metadata."""
    response = preset["response"]
    meta = response["metadata"]
    return {
        "session_id": "demo-session-a1b2c3d4",
        "message": "Demo summary",
        "sources": ["orders"],
        "sql": response["sql"],
        "results": response["results"][:5],
        "columns": response["columns"],
        "chart": response.get("chart"),
        "metadata": {
            "database_id": "default",
            "row_count": meta["row_count"],
            "execution_time_ms": meta["execution_time_ms"],
            "truncated": meta["truncated"],
            "warnings": meta.get("warnings", []),
            "repair_attempts": meta.get("repair_attempts", 0),
            "used_sql": True,
            "enhancement": {"enabled": True, "applied": ["schema_aware", "multi_turn"]},
            "scope": {"in_scope": True, "reason": "in_scope", "source": "heuristic"},
        },
    }


def test_demo_preset_stream_meta_validates(fixtures_data: dict) -> None:
    for preset in fixtures_data["presets"]:
        chat = _demo_chat_response_from_preset(preset)
        stream_meta = chat_response_to_stream_meta(chat)
        errors = validate_chat_stream_meta(stream_meta)
        assert not errors, f"preset {preset['id']} stream meta: {errors}"


def test_bar_missing_encoding_fails() -> None:
    payload = {
        "sql": "SELECT a, b FROM t",
        "columns": [],
        "results": [{"a": 1, "b": 2}],
        "chart": {
            "chart_type": "bar",
            "vega_lite_spec": {"$schema": "https://vega.github.io/schema/vega-lite/v5.json"},
            "metadata": {"x_field": "a", "y_field": "b"},
        },
        "metadata": _query_metadata(),
    }
    errors = validate_query_response(payload)
    assert any("encoding" in e for e in errors)
