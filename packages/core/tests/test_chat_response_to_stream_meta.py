"""Parity tests for flattening ChatResponse JSON to seal.meta."""

from __future__ import annotations

from seal_core.pipeline.execute import ExecuteQueryResult
from seal_core.pipeline.models import build_chat_metadata, build_stream_meta_event
from seal_core.pipeline.validate_metadata import (
    chat_response_to_stream_meta,
    validate_stream_meta_event,
)
from seal_core.planner.models import ChartType, QueryPlan
from seal_sql.result import ColumnMetadata


def _exec_result() -> ExecuteQueryResult:
    return ExecuteQueryResult(
        sql="SELECT COUNT(*) AS n FROM orders",
        columns=[ColumnMetadata("n", "int8")],
        rows=[{"n": 10}],
        plan=QueryPlan(
            sql="SELECT COUNT(*) AS n FROM orders",
            chart_type=ChartType.TABLE,
            title="Orders",
            explanation="count",
        ),
        row_count=1,
        execution_time_ms=2.0,
        truncated=False,
        warnings=[],
        repair_attempts=1,
    )


def test_chat_response_to_stream_meta_matches_build_stream_meta_event() -> None:
    exec_result = _exec_result()
    scope = {"in_scope": True, "reason": "in_scope", "source": "heuristic"}
    metadata = build_chat_metadata(
        database_id="default",
        exec_result=exec_result,
        used_sql=True,
        enhancement_enabled=True,
        applied=["schema_aware"],
        scope=scope,
        vector_rag_available=True,
        orchestrator_available=True,
    )
    chat_response = {
        "session_id": "demo-session-a1b2c3d4",
        "message": "There are 10 orders.",
        "sources": ["orders"],
        "sql": exec_result.sql,
        "results": exec_result.rows,
        "columns": [{"name": "n", "type": "int8", "nullable": True}],
        "chart": None,
        "metadata": metadata,
    }
    flattened = chat_response_to_stream_meta(chat_response)
    built = build_stream_meta_event(
        session_id="demo-session-a1b2c3d4",
        database_id="default",
        exec_result=exec_result,
        used_sql=True,
        enhancement_enabled=True,
        applied=["schema_aware"],
        sources=["orders"],
        sql=exec_result.sql,
        results=exec_result.rows,
        columns=[{"name": "n", "type": "int8", "nullable": True}],
        chart=None,
        scope=scope,
        vector_rag_available=True,
        orchestrator_available=True,
    )
    assert flattened == built
    assert not validate_stream_meta_event(flattened)


def test_chat_response_to_stream_meta_includes_refusal_flags() -> None:
    metadata = build_chat_metadata(
        database_id="default",
        exec_result=None,
        used_sql=False,
        enhancement_enabled=False,
        applied=[],
        scope={"in_scope": False, "reason": "off-topic", "source": "heuristic"},
        refusal=True,
        vector_rag_available=False,
        orchestrator_available=False,
        enhancement_requested=True,
    )
    flat = chat_response_to_stream_meta(
        {
            "session_id": "s-refusal",
            "message": "I cannot help with that.",
            "metadata": metadata,
        }
    )
    assert flat["refusal"] is True
    assert flat["enhancement"]["unavailable_reason"] == "orchestrator_unavailable"
    assert not validate_stream_meta_event(flat)
