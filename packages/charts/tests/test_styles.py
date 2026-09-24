"""Tests for chart style templates and color schemes."""

from seal_charts.heuristics import HeuristicsResult
from seal_charts.models import ChartStyleOptions
from seal_charts.samples import styled_bar_sample
from seal_charts.styles import (
    ChartColorScheme,
    ChartTemplate,
    apply_chart_style,
    get_style_catalog,
)
from seal_core.planner.models import ChartType


def test_style_catalog_lists_templates_and_schemes() -> None:
    catalog = get_style_catalog()
    template_ids = {t["id"] for t in catalog["templates"]}
    scheme_ids = {s["id"] for s in catalog["color_schemes"]}
    assert template_ids == {"default", "minimal", "bold", "rounded"}
    assert scheme_ids == {
        "category10",
        "tableau10",
        "set2",
        "viridis",
        "blues",
        "oranges",
    }
    for scheme in catalog["color_schemes"]:
        assert len(scheme["swatches"]) >= 3


def test_apply_chart_style_bar_adds_scheme_and_config() -> None:
    base_spec = {
        "mark": {"type": "bar", "tooltip": True},
        "encoding": {
            "x": {"field": "category", "type": "nominal"},
            "y": {"field": "total_revenue", "type": "quantitative"},
        },
    }
    heuristics = HeuristicsResult(
        chart_type=ChartType.BAR,
        x_field="category",
        y_field="total_revenue",
        color_field=None,
    )
    style = ChartStyleOptions(
        template=ChartTemplate.ROUNDED,
        color_scheme=ChartColorScheme.TABLEAU10,
    )
    styled = apply_chart_style(base_spec, style, heuristics)

    assert styled["mark"]["cornerRadiusEnd"] == 4
    color = styled["encoding"]["color"]
    assert color["field"] == "category"
    assert color["scale"]["scheme"] == "tableau10"


def test_apply_chart_style_line_uses_single_color_value() -> None:
    base_spec = {
        "mark": {"type": "line", "tooltip": True},
        "encoding": {
            "x": {"field": "hour", "type": "temporal"},
            "y": {"field": "event_count", "type": "quantitative"},
        },
    }
    heuristics = HeuristicsResult(
        chart_type=ChartType.LINE,
        x_field="hour",
        y_field="event_count",
        color_field=None,
    )
    style = ChartStyleOptions(color_scheme=ChartColorScheme.VIRIDIS)
    styled = apply_chart_style(base_spec, style, heuristics)

    assert styled["encoding"]["color"]["value"] == "#440154"


def test_apply_chart_style_pie_adds_color_scale() -> None:
    base_spec = {
        "mark": {"type": "arc", "innerRadius": 50, "tooltip": True},
        "encoding": {
            "theta": {"field": "orders", "type": "quantitative"},
            "color": {"field": "region", "type": "nominal"},
        },
    }
    heuristics = HeuristicsResult(
        chart_type=ChartType.PIE,
        x_field="region",
        y_field="orders",
        color_field=None,
    )
    style = ChartStyleOptions(color_scheme=ChartColorScheme.SET2)
    styled = apply_chart_style(base_spec, style, heuristics)

    assert styled["encoding"]["color"]["scale"]["scheme"] == "set2"


def test_styled_bar_sample_includes_config_and_color() -> None:
    spec = styled_bar_sample()
    assert spec["encoding"]["color"]["scale"]["scheme"] == "tableau10"
    assert spec["mark"]["cornerRadiusEnd"] == 4
