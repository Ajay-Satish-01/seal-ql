"""Tests for shared ExecutionMetadata builders."""

from __future__ import annotations

from seal_core.pipeline.execute import ExecuteQueryResult
from seal_core.pipeline.models import (
    ENHANCEMENT_UNAVAILABLE_ORCHESTRATOR,
    VECTOR_SKIPPED_NON_DEFAULT,
    VECTOR_SKIPPED_VECTOR_STORE_DISABLED,
    ExecutionMetadata,
    build_chat_metadata,
    build_enhancement_metadata,
)
from seal_core.planner.models import ChartType, QueryPlan
from seal_sql.result import ColumnMetadata


def _exec_result(*, repair_attempts: int = 1) -> ExecuteQueryResult:
    return ExecuteQueryResult(
        sql="SELECT 1",
        columns=[ColumnMetadata("id", "int")],
        rows=[{"id": 1}],
        plan=QueryPlan(
            sql="SELECT 1",
            chart_type=ChartType.TABLE,
            title="t",
            explanation="e",
        ),
        row_count=1,
        execution_time_ms=12.5,
        truncated=True,
        warnings=["limit applied"],
        repair_attempts=repair_attempts,
    )


def test_execution_metadata_from_execute_result() -> None:
    meta = ExecutionMetadata.from_execute_result(
        database_id="analytics",
        exec_result=_exec_result(repair_attempts=2),
        used_sql=True,
    )
    assert meta.database_id == "analytics"
    assert meta.row_count == 1
    assert meta.execution_time_ms == 12.5
    assert meta.truncated is True
    assert meta.warnings == ["limit applied"]
    assert meta.repair_attempts == 2
    assert meta.used_sql is True


def test_build_enhancement_metadata_vector_skipped_on_non_default() -> None:
    enh = build_enhancement_metadata(
        enabled=True,
        applied=["schema_aware"],
        database_id="warehouse",
        vector_rag_available=True,
        orchestrator_available=True,
    )
    assert enh.enabled is True
    assert enh.applied == ["schema_aware"]
    assert enh.vector_skipped_reason == VECTOR_SKIPPED_NON_DEFAULT


def test_build_enhancement_metadata_no_vector_skip_when_disabled() -> None:
    enh = build_enhancement_metadata(
        enabled=False,
        applied=[],
        database_id="warehouse",
        vector_rag_available=True,
        orchestrator_available=True,
    )
    assert enh.vector_skipped_reason is None


def test_build_enhancement_metadata_vector_store_disabled_on_default() -> None:
    enh = build_enhancement_metadata(
        enabled=True,
        applied=[],
        database_id="default",
        vector_rag_available=False,
        orchestrator_available=True,
    )
    assert enh.vector_skipped_reason == VECTOR_SKIPPED_VECTOR_STORE_DISABLED


def test_build_enhancement_metadata_unavailable_when_requested_without_orchestrator() -> None:
    enh = build_enhancement_metadata(
        enabled=False,
        applied=[],
        database_id="default",
        vector_rag_available=False,
        enhancement_requested=True,
        orchestrator_available=False,
    )
    assert enh.unavailable_reason == ENHANCEMENT_UNAVAILABLE_ORCHESTRATOR


def test_build_enhancement_metadata_no_unavailable_when_orchestrator_present_but_disabled() -> None:
    """Refusal turns pass enabled=False while orchestrator exists; must not set unavailable."""
    enh = build_enhancement_metadata(
        enabled=False,
        applied=[],
        database_id="default",
        vector_rag_available=True,
        enhancement_requested=True,
        orchestrator_available=True,
    )
    assert enh.unavailable_reason is None


def test_build_enhancement_metadata_no_skip_on_default() -> None:
    enh = build_enhancement_metadata(
        enabled=True,
        applied=["vector_rag"],
        database_id="default",
        vector_rag_available=True,
        orchestrator_available=True,
    )
    assert enh.vector_skipped_reason is None


def test_build_chat_metadata_includes_enhancement_and_scope() -> None:
    payload = build_chat_metadata(
        database_id="default",
        exec_result=_exec_result(),
        used_sql=True,
        enhancement_enabled=True,
        applied=["multi_turn"],
        scope={"in_scope": True, "reason": None, "source": "heuristic"},
        vector_rag_available=True,
        orchestrator_available=True,
    )
    assert payload["row_count"] == 1
    assert payload["repair_attempts"] == 1
    assert payload["used_sql"] is True
    assert payload["enhancement"]["enabled"] is True
    assert payload["enhancement"]["applied"] == ["multi_turn"]
    assert payload["scope"]["in_scope"] is True


def test_execution_metadata_includes_provenance_fields() -> None:
    result = _exec_result()
    result.tables_used = ["orders"]
    result.columns_used = ["orders.id"]
    meta = ExecutionMetadata.from_execute_result(
        database_id="default",
        exec_result=result,
        used_sql=True,
        catalog_matches=[{"name": "orders", "schema": "public", "description": "Sales"}],
    )
    assert meta.tables_used == ["orders"]
    assert meta.columns_used == ["orders.id"]
    assert meta.catalog_matches[0].name == "orders"


def test_build_chat_metadata_includes_reasoning() -> None:
    from seal_core.reasoning.models import ReasoningMetadata

    payload = build_chat_metadata(
        database_id="default",
        exec_result=None,
        used_sql=False,
        enhancement_enabled=True,
        reasoning=ReasoningMetadata(
            clarification_required=True,
            clarifying_questions=["What time range?"],
            layers_applied=["clarification"],
        ),
        vector_rag_available=True,
        orchestrator_available=True,
    )
    assert payload["reasoning"]["clarification_required"] is True
    assert payload["reasoning"]["clarifying_questions"] == ["What time range?"]
