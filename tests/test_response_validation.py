"""Tests for QueryResponse and demo fixture validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from response_validation import validate_query_response  # noqa: E402

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


def test_null_chart_allowed() -> None:
    payload = {
        "sql": "SELECT 1",
        "columns": [{"name": "x", "type": "int"}],
        "results": [],
        "chart": None,
        "metadata": {},
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
        "metadata": {"row_count": 1},
    }
    assert not validate_query_response(payload)


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
        "metadata": {},
    }
    errors = validate_query_response(payload)
    assert any("encoding" in e for e in errors)
