"""Tests for heuristic guardrails query suggestions."""

from __future__ import annotations

from seal_core.guardrails.models import ScopeCategory, ScopeResult
from seal_core.guardrails.scope import build_query_out_of_scope_detail
from seal_core.guardrails.suggestions import merge_suggestions, suggest_queries


def test_suggest_queries_limits_source() -> None:
    scope = ScopeResult(in_scope=False, reason="query exceeds 4000 characters", source="limits")
    assert len(suggest_queries(scope)) <= 3
    assert "month" in suggest_queries(scope)[0].lower()


def test_suggest_queries_off_topic_reason_fallback() -> None:
    scope = ScopeResult(in_scope=False, reason="off-topic pattern", source="heuristic")
    suggestions = suggest_queries(scope)
    assert any("schema" in s.lower() for s in suggestions)


def test_suggest_queries_abuse_category() -> None:
    scope = ScopeResult(
        in_scope=False,
        reason="off-topic pattern",
        source="heuristic",
        category=ScopeCategory.ABUSE,
    )
    suggestions = suggest_queries(scope)
    assert len(suggestions) == 3
    assert any("orders" in s.lower() for s in suggestions)


def test_merge_suggestions_prefers_llm() -> None:
    heuristic = ["A", "B", "C"]
    llm = ["Custom question"]
    assert merge_suggestions(heuristic, llm) == ["Custom question"]


def test_merge_suggestions_falls_back_to_heuristic() -> None:
    heuristic = ["A", "B"]
    assert merge_suggestions(heuristic, []) == heuristic


def test_merge_suggestions_truncates_long_llm_strings() -> None:
    long = "x" * 500
    merged = merge_suggestions(["Short"], [long])
    assert len(merged) == 1
    assert len(merged[0]) == 200


def test_merge_suggestions_caps_at_three() -> None:
    merged = merge_suggestions([], ["a", "b", "c", "d", "e"])
    assert merged == ["a", "b", "c"]


def test_build_query_out_of_scope_detail_shape() -> None:
    scope = ScopeResult(in_scope=False, reason="off-topic", source="heuristic")
    detail = build_query_out_of_scope_detail(scope)
    assert detail["detail"] == "query_out_of_scope"
    assert detail["reason"] == "off-topic"
    assert isinstance(detail["suggested_queries"], list)
    assert len(detail["suggested_queries"]) <= 3
