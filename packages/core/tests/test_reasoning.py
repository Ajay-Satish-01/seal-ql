"""Tests for layered reasoning orchestration."""

from __future__ import annotations

import pytest
from seal_core.reasoning.clarification_response import should_probe_schema_for_clarification
from seal_core.reasoning.config import resolve_reasoning_config
from seal_core.reasoning.layers import ClarificationLayer, InferredContextLayer
from seal_core.reasoning.merge import merge_reasoning_metadata
from seal_core.reasoning.models import (
    DatabaseCapabilities,
    ReasoningContext,
    ReasoningLayerResult,
    ReasoningMetadata,
    ReasoningPhase,
    format_reasoning_message,
    merge_reasoning_results,
    normalize_reasoning_clarification,
    should_return_clarification,
)
from seal_core.reasoning.orchestrator import ReasoningOrchestrator, build_default_orchestrator
from seal_core.settings import clear_settings_cache


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv("REASONING_ENABLED", "true")
    monkeypatch.setenv("REASONING_CLARIFICATION_ENABLED", "true")


@pytest.mark.asyncio
async def test_clarification_layer_flags_ambiguous_chat_message() -> None:
    layer = ClarificationLayer()
    ctx = ReasoningContext(
        route="chat",
        user_message="How is it performing compared to that period?",
        database_capabilities=DatabaseCapabilities.from_bundle(
            database_id="default",
            dialect="postgres",
        ),
        phase=ReasoningPhase.PRE_EXECUTION,
    )
    result = await layer.run(ctx)
    assert result.clarification_required is True
    assert result.clarifying_questions


@pytest.mark.asyncio
async def test_inferred_context_layer_chat_only() -> None:
    from seal_core.chat.models import ChatMessage

    layer = InferredContextLayer()
    ctx = ReasoningContext(
        route="chat",
        user_message="And what about last month?",
        database_capabilities=DatabaseCapabilities.from_bundle(
            database_id="default",
            dialect="postgres",
        ),
        phase=ReasoningPhase.PRE_EXECUTION,
        messages=(
            ChatMessage(role="user", content="Show revenue by region"),
            ChatMessage(role="assistant", content="Revenue was highest in the west region."),
        ),
    )
    result = await layer.run(ctx)
    assert result.inferred_context
    assert "west" in result.inferred_context[0].lower()


@pytest.mark.asyncio
async def test_orchestrator_pre_phase_merges_layers() -> None:
    orchestrator = build_default_orchestrator()
    ctx = ReasoningContext(
        route="query",
        user_message="show me trends",
        database_capabilities=DatabaseCapabilities.from_bundle(
            database_id="default",
            dialect="duckdb",
        ),
        phase=ReasoningPhase.PRE_EXECUTION,
        schema_table_count=12,
    )
    reasoning = await orchestrator.run_pre(ctx)
    assert isinstance(reasoning.layers_applied, list)
    assert reasoning.clarification_required is True


def test_format_reasoning_message_includes_sections() -> None:
    from seal_core.reasoning.models import ReasoningMetadata

    text = format_reasoning_message(
        ReasoningMetadata(
            clarifying_questions=["What time range?"],
            clarification_required=True,
            analysis_followups=["Compare by segment"],
        )
    )
    assert "A few details would help" in text
    assert "Suggested follow-ups" in text


def test_resolve_reasoning_config_disables_query_when_flag_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_settings_cache()
    monkeypatch.setenv("REASONING_QUERY_ENABLED", "false")
    cfg = resolve_reasoning_config("query")
    assert cfg.enabled is False


def test_resolve_reasoning_config_chat_defers_post_layers_to_answer_llm() -> None:
    chat_cfg = resolve_reasoning_config("chat")
    query_cfg = resolve_reasoning_config("query")
    assert chat_cfg.analysis_followups_enabled is False
    assert chat_cfg.research_notes_enabled is False
    assert query_cfg.analysis_followups_enabled is True
    assert query_cfg.research_notes_enabled is True


def test_merge_answer_reasoning_replaces_pipeline_followups() -> None:
    from seal_core.reasoning.merge import merge_answer_reasoning

    merged = merge_answer_reasoning(
        ReasoningMetadata(
            analysis_followups=["Layer follow-up"],
            research_notes=["Layer note"],
            layers_applied=["analysis_followups"],
        ),
        ReasoningMetadata(
            analysis_followups=["LLM follow-up"],
            research_notes=["LLM note"],
            layers_applied=["chat_answer_llm"],
        ),
    )
    assert merged.analysis_followups == ["LLM follow-up"]
    assert merged.research_notes == ["LLM note"]
    assert "analysis_followups" in merged.layers_applied


def test_merge_reasoning_results_dedupes() -> None:
    from seal_core.reasoning.models import ReasoningLayerResult

    merged = merge_reasoning_results(
        [
            ReasoningLayerResult(
                clarifying_questions=["What time range?", "What time range?"],
                layer_name="a",
            ),
            ReasoningLayerResult(
                analysis_followups=["Segment breakdown"],
                layer_name="b",
            ),
        ]
    )
    assert len(merged.clarifying_questions) == 1
    assert merged.analysis_followups == ["Segment breakdown"]


@pytest.mark.asyncio
async def test_short_specific_query_does_not_clarify() -> None:
    layer = ClarificationLayer()
    ctx = ReasoningContext(
        route="query",
        user_message="top orders",
        database_capabilities=DatabaseCapabilities.from_bundle(
            database_id="default",
            dialect="postgres",
        ),
        phase=ReasoningPhase.PRE_EXECUTION,
    )
    result = await layer.run(ctx)
    assert result.clarification_required is False


@pytest.mark.asyncio
async def test_query_pronoun_with_ambiguity_clarifies() -> None:
    layer = ClarificationLayer()
    ctx = ReasoningContext(
        route="query",
        user_message="How is it performing compared to that period?",
        database_capabilities=DatabaseCapabilities.from_bundle(
            database_id="default",
            dialect="postgres",
        ),
        phase=ReasoningPhase.PRE_EXECUTION,
    )
    result = await layer.run(ctx)
    assert result.clarification_required is True


def test_merge_reasoning_metadata_preserves_layers_applied() -> None:
    from seal_core.reasoning.models import ReasoningLayerResult

    merged = merge_reasoning_metadata(
        ReasoningMetadata(layers_applied=["clarification"], clarifying_questions=["A?"]),
        ReasoningLayerResult(analysis_followups=["Follow up"], layer_name="analysis_followups"),
    )
    assert merged.layers_applied == ["clarification", "analysis_followups"]


def test_normalize_reasoning_clarification_adds_default_question() -> None:
    reasoning = ReasoningMetadata(clarification_required=True)
    normalized = normalize_reasoning_clarification(reasoning)
    assert should_return_clarification(normalized) is True
    assert normalized.clarifying_questions


@pytest.mark.asyncio
async def test_research_notes_hide_tables_when_trust_off(monkeypatch: pytest.MonkeyPatch) -> None:
    from seal_core.pipeline.execute import ExecuteQueryResult
    from seal_core.pipeline.trust import strip_trust_reasoning
    from seal_core.planner.models import ChartType, QueryPlan
    from seal_core.reasoning.layers import ResearchNotesLayer

    monkeypatch.setenv("SEAL_TRUST_EXPLAINABILITY_ENABLED", "false")
    clear_settings_cache()
    layer = ResearchNotesLayer()
    exec_result = ExecuteQueryResult(
        sql="SELECT 1",
        columns=[],
        rows=[],
        plan=QueryPlan(sql="SELECT 1", chart_type=ChartType.TABLE, title="t"),
        row_count=0,
        execution_time_ms=1.0,
        truncated=False,
        tables_used=["orders", "customers"],
    )
    ctx = ReasoningContext(
        route="query",
        user_message="count orders",
        database_capabilities=DatabaseCapabilities.from_bundle(
            database_id="default",
            dialect="postgres",
        ),
        phase=ReasoningPhase.POST_EXECUTION,
        exec_result=exec_result,
    )
    result = await layer.run(ctx)
    assert not any("Data sourced from" in note for note in result.research_notes)

    gated = strip_trust_reasoning(
        {
            "research_notes": ["Data sourced from: orders.", "Query returned 1 row(s)."],
        }
    )
    assert gated["research_notes"] == ["Query returned 1 row(s)."]


@pytest.mark.asyncio
async def test_orchestrator_disabled_when_reasoning_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REASONING_ENABLED", "false")
    clear_settings_cache()
    orchestrator = build_default_orchestrator()
    ctx = ReasoningContext(
        route="query",
        user_message="show me trends",
        database_capabilities=DatabaseCapabilities.from_bundle(
            database_id="default",
            dialect="postgres",
        ),
        phase=ReasoningPhase.PRE_EXECUTION,
    )
    reasoning = await orchestrator.run_pre(ctx)
    assert reasoning.layers_applied == []
    assert reasoning.clarification_required is False


@pytest.mark.asyncio
async def test_custom_layer_registration() -> None:
    class EchoLayer:
        name = "echo"
        phase = ReasoningPhase.POST_EXECUTION

        def enabled(self, ctx: ReasoningContext) -> bool:
            return True

        async def run(self, ctx: ReasoningContext):
            from seal_core.reasoning.models import ReasoningLayerResult

            return ReasoningLayerResult(
                research_notes=[f"route={ctx.route}"],
                layer_name=self.name,
            )

    orchestrator = ReasoningOrchestrator(layers=[EchoLayer()])
    ctx = ReasoningContext(
        route="query",
        user_message="count orders",
        database_capabilities=DatabaseCapabilities.from_bundle(
            database_id="default",
            dialect="postgres",
        ),
        phase=ReasoningPhase.POST_EXECUTION,
    )
    reasoning = await orchestrator.run_post(ctx)
    assert reasoning.research_notes == ["route=query"]


def test_should_probe_schema_for_clarification_is_selective() -> None:
    assert should_probe_schema_for_clarification("overview") is True
    assert should_probe_schema_for_clarification("How many orders last month?") is False


@pytest.mark.asyncio
async def test_run_clarification_only_records_telemetry() -> None:
    from unittest.mock import patch

    orchestrator = build_default_orchestrator()
    ctx = ReasoningContext(
        route="query",
        user_message="show me trends",
        database_capabilities=DatabaseCapabilities.from_bundle(
            database_id="default",
            dialect="postgres",
        ),
        phase=ReasoningPhase.PRE_EXECUTION,
        schema_table_count=16,
    )
    with patch("seal_core.reasoning.orchestrator.record_reasoning_phase") as telemetry:
        reasoning = await orchestrator.run_clarification_only(ctx)
    assert telemetry.call_count == 1
    assert reasoning.layers_applied == ["clarification"]


@pytest.mark.asyncio
async def test_latency_budget_skips_layers_when_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Layers beyond the budget are marked unavailable, not silently dropped."""
    import asyncio

    monkeypatch.setenv("REASONING_LATENCY_BUDGET_MS", "1")
    clear_settings_cache()

    class SlowLayer:
        name = "slow"
        phase = ReasoningPhase.POST_EXECUTION

        def enabled(self, ctx: ReasoningContext) -> bool:
            return True

        async def run(self, ctx: ReasoningContext) -> ReasoningLayerResult:
            await asyncio.sleep(0.05)
            return ReasoningLayerResult(
                research_notes=["slow note"],
                layer_name=self.name,
            )

    class FastLayer:
        name = "fast"
        phase = ReasoningPhase.POST_EXECUTION

        def enabled(self, ctx: ReasoningContext) -> bool:
            return True

        async def run(self, ctx: ReasoningContext) -> ReasoningLayerResult:
            return ReasoningLayerResult(
                research_notes=["fast note"],
                layer_name=self.name,
            )

    orchestrator = ReasoningOrchestrator(layers=[SlowLayer(), FastLayer()])
    ctx = ReasoningContext(
        route="query",
        user_message="count orders",
        database_capabilities=DatabaseCapabilities.from_bundle(
            database_id="default",
            dialect="postgres",
        ),
        phase=ReasoningPhase.POST_EXECUTION,
    )
    reasoning = await orchestrator.run_post(ctx)
    assert "slow" in reasoning.layers_applied
    assert "fast" not in reasoning.layers_applied
    assert reasoning.layers_unavailable.get("fast") == "latency_budget_exceeded"


def test_trust_gating_strips_table_parenthetical_notes() -> None:
    """Ensure 'table(s)' phrasing is caught by trust gating."""
    from seal_core.pipeline.trust import strip_trust_reasoning

    gated = strip_trust_reasoning(
        {
            "research_notes": [
                "Schema exposes 14 table(s) on postgres (postgres).",
                "Query returned 5 row(s) in 12.3 ms.",
            ],
        }
    )
    assert len(gated["research_notes"]) == 1
    assert "row(s)" in gated["research_notes"][0]


def test_reasoning_context_is_immutable() -> None:
    """ReasoningContext should not allow in-place mutation."""
    from dataclasses import FrozenInstanceError, replace

    ctx = ReasoningContext(
        route="query",
        user_message="test",
        database_capabilities=DatabaseCapabilities.from_bundle(
            database_id="default",
            dialect="postgres",
        ),
        phase=ReasoningPhase.PRE_EXECUTION,
    )
    with pytest.raises(FrozenInstanceError):
        ctx.phase = ReasoningPhase.POST_EXECUTION  # type: ignore[misc]

    new_ctx = replace(ctx, phase=ReasoningPhase.POST_EXECUTION)
    assert new_ctx.phase == ReasoningPhase.POST_EXECUTION
    assert ctx.phase == ReasoningPhase.PRE_EXECUTION
