"""Golden fixture tests for chart style application."""

from __future__ import annotations

import json
from pathlib import Path

from seal_charts.heuristics import HeuristicsResult
from seal_charts.models import ChartStyleOptions
from seal_charts.styles import ChartColorScheme, ChartTemplate, apply_chart_style
from seal_core.planner.models import ChartType

_FIXTURE = Path(__file__).parent / "fixtures" / "chart_style_bar_case.json"


def test_apply_chart_style_matches_golden_fixture() -> None:
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    heuristics = HeuristicsResult(
        chart_type=ChartType(data["heuristics"]["chart_type"]),
        x_field=data["heuristics"]["x_field"],
        y_field=data["heuristics"]["y_field"],
        color_field=data["heuristics"]["color_field"],
    )
    style = ChartStyleOptions(
        template=ChartTemplate(data["style"]["template"]),
        color_scheme=ChartColorScheme(data["style"]["color_scheme"]),
    )

    styled = apply_chart_style(data["base_spec"], style, heuristics)
    expected = data["expected"]

    assert styled["mark"]["cornerRadiusEnd"] == expected["mark"]["cornerRadiusEnd"]
    assert styled["encoding"]["color"] == expected["encoding"]["color"]
