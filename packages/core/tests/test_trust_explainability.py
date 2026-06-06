"""Tests for trust/explainability gating."""

from __future__ import annotations

import pytest
from seal_core.pipeline.trust import (
    apply_trust_gating_to_chat_response,
    apply_trust_gating_to_metadata,
    apply_trust_gating_to_query_response,
    apply_trust_gating_to_stream_meta,
)
from seal_core.settings import clear_settings_cache


@pytest.fixture(autouse=True)
def _reset_settings() -> None:
    clear_settings_cache()
    yield
    clear_settings_cache()


def test_apply_trust_gating_strips_metadata_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEAL_TRUST_EXPLAINABILITY_ENABLED", "false")
    clear_settings_cache()

    meta = {
        "database_id": "default",
        "row_count": 1,
        "repair_attempts": 2,
        "tables_used": ["orders"],
        "columns_used": ["orders.id"],
        "catalog_matches": [{"name": "orders", "schema": "public"}],
        "scope": {"in_scope": True, "source": "heuristic"},
    }
    gated = apply_trust_gating_to_metadata(meta)
    assert gated["row_count"] == 1
    assert "repair_attempts" not in gated
    assert "tables_used" not in gated
    assert "scope" not in gated


def test_apply_trust_gating_preserves_metadata_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SEAL_TRUST_EXPLAINABILITY_ENABLED", "true")
    clear_settings_cache()

    meta = {"repair_attempts": 1, "tables_used": ["orders"]}
    gated = apply_trust_gating_to_metadata(meta)
    assert gated == meta


def test_apply_trust_gating_to_chat_response_strips_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEAL_TRUST_EXPLAINABILITY_ENABLED", "false")
    clear_settings_cache()

    response = {
        "session_id": "s1",
        "message": "hi",
        "sources": ["orders"],
        "sql": "SELECT 1",
        "results": [{"n": 1}],
        "columns": [{"name": "n", "type": "int"}],
        "metadata": {"repair_attempts": 0, "scope": {"in_scope": True, "source": "heuristic"}},
    }
    gated = apply_trust_gating_to_chat_response(response)
    assert gated["sources"] == []
    assert gated["sql"] is None
    assert gated["results"] is None
    assert "scope" not in gated["metadata"]


def test_apply_trust_gating_to_query_response_keeps_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEAL_TRUST_EXPLAINABILITY_ENABLED", "false")
    clear_settings_cache()

    response = {
        "sql": "SELECT 1",
        "results": [{"n": 1}],
        "sources": ["orders"],
        "metadata": {"repair_attempts": 0, "tables_used": ["orders"]},
    }
    gated = apply_trust_gating_to_query_response(response)
    assert gated["sql"] == "SELECT 1"
    assert gated["sources"] == []
    assert "tables_used" not in gated["metadata"]


def test_apply_trust_gating_to_stream_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEAL_TRUST_EXPLAINABILITY_ENABLED", "false")
    clear_settings_cache()

    event = {
        "session_id": "s1",
        "sql": "SELECT 1",
        "sources": ["orders"],
        "repair_attempts": 0,
        "tables_used": ["orders"],
    }
    gated = apply_trust_gating_to_stream_meta(event)
    assert gated["session_id"] == "s1"
    assert "sql" not in gated
    assert "sources" not in gated
    assert "tables_used" not in gated
