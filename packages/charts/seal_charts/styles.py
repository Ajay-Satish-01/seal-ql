"""Chart style templates and color schemes for Vega-Lite specs."""

from __future__ import annotations

import copy
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from seal_core.planner.models import ChartType

if TYPE_CHECKING:
    from seal_charts.heuristics import HeuristicsResult
    from seal_charts.models import ChartStyleOptions


class ChartTemplate(StrEnum):
    DEFAULT = "default"
    MINIMAL = "minimal"
    BOLD = "bold"
    ROUNDED = "rounded"


class ChartColorScheme(StrEnum):
    CATEGORY10 = "category10"
    TABLEAU10 = "tableau10"
    SET2 = "set2"
    VIRIDIS = "viridis"
    BLUES = "blues"
    ORANGES = "oranges"


# Preview swatches for UI (first colors from each Vega scheme).
SCHEME_SWATCHES: dict[ChartColorScheme, list[str]] = {
    ChartColorScheme.CATEGORY10: [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
    ],
    ChartColorScheme.TABLEAU10: [
        "#4e79a7",
        "#f28e2b",
        "#e15759",
        "#76b7b2",
        "#59a14f",
    ],
    ChartColorScheme.SET2: ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854"],
    ChartColorScheme.VIRIDIS: ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"],
    ChartColorScheme.BLUES: ["#c6dbef", "#6baed6", "#3182bd", "#08519c", "#08306b"],
    ChartColorScheme.ORANGES: ["#fdd0a2", "#fdae6b", "#fd8d3c", "#e6550d", "#a63603"],
}

TEMPLATE_LABELS: dict[ChartTemplate, str] = {
    ChartTemplate.DEFAULT: "Default",
    ChartTemplate.MINIMAL: "Minimal",
    ChartTemplate.BOLD: "Bold",
    ChartTemplate.ROUNDED: "Rounded",
}

TEMPLATE_DESCRIPTIONS: dict[ChartTemplate, str] = {
    ChartTemplate.DEFAULT: "Standard axes and title styling.",
    ChartTemplate.MINIMAL: "Clean look with no grid lines or axis domain.",
    ChartTemplate.BOLD: "Larger title and axis labels.",
    ChartTemplate.ROUNDED: "Rounded bar corners with standard axes.",
}

SCHEME_LABELS: dict[ChartColorScheme, str] = {
    ChartColorScheme.CATEGORY10: "Category 10",
    ChartColorScheme.TABLEAU10: "Tableau 10",
    ChartColorScheme.SET2: "Set 2",
    ChartColorScheme.VIRIDIS: "Viridis",
    ChartColorScheme.BLUES: "Blues",
    ChartColorScheme.ORANGES: "Oranges",
}

_TEMPLATE_CONFIGS: dict[ChartTemplate, dict[str, Any]] = {
    ChartTemplate.DEFAULT: {},
    ChartTemplate.MINIMAL: {
        "axis": {"grid": False, "domain": False},
        "view": {"stroke": "transparent"},
    },
    ChartTemplate.BOLD: {
        "title": {"fontSize": 16, "fontWeight": "bold"},
        "axis": {"labelFontSize": 12, "titleFontSize": 13},
    },
    ChartTemplate.ROUNDED: {},
}

_TEMPLATE_MARK: dict[ChartTemplate, dict[str, Any]] = {
    ChartTemplate.ROUNDED: {"cornerRadiusEnd": 4},
}


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def get_style_catalog() -> dict[str, Any]:
    """Return templates and color schemes for GET /v1/charts/styles."""
    return {
        "templates": [
            {
                "id": t.value,
                "label": TEMPLATE_LABELS[t],
                "description": TEMPLATE_DESCRIPTIONS[t],
            }
            for t in ChartTemplate
        ],
        "color_schemes": [
            {
                "id": s.value,
                "label": SCHEME_LABELS[s],
                "swatches": SCHEME_SWATCHES[s],
            }
            for s in ChartColorScheme
        ],
    }


def apply_chart_style(
    spec: dict[str, Any],
    style: ChartStyleOptions,
    heuristics: HeuristicsResult,
) -> dict[str, Any]:
    """Merge template config, mark tweaks, and color scheme into a Vega-Lite spec."""
    if not spec:
        return spec

    styled = copy.deepcopy(spec)
    template = style.template
    scheme = style.color_scheme.value
    primary_color = SCHEME_SWATCHES[style.color_scheme][0]

    template_config = _TEMPLATE_CONFIGS.get(template, {})
    if template_config:
        styled["config"] = _deep_merge(styled.get("config", {}), template_config)

    mark_overlay = _TEMPLATE_MARK.get(template, {})
    if mark_overlay and isinstance(styled.get("mark"), dict):
        mark_type = styled["mark"].get("type")
        if mark_type == "bar":
            styled["mark"] = _deep_merge(styled["mark"], mark_overlay)

    encoding = styled.setdefault("encoding", {})
    chart_type = heuristics.chart_type

    if chart_type == ChartType.PIE:
        color_enc = encoding.get("color")
        if isinstance(color_enc, dict) and "field" in color_enc:
            color_enc = copy.deepcopy(color_enc)
            color_enc["scale"] = {"scheme": scheme}
            encoding["color"] = color_enc
    elif chart_type == ChartType.BAR:
        color_enc = encoding.get("color")
        if isinstance(color_enc, dict) and color_enc.get("field"):
            color_enc = copy.deepcopy(color_enc)
            color_enc["scale"] = {"scheme": scheme}
            encoding["color"] = color_enc
        elif heuristics.x_field:
            x_enc = encoding.get("x")
            x_type = x_enc.get("type") if isinstance(x_enc, dict) else None
            if x_type == "nominal":
                encoding["color"] = {
                    "field": heuristics.x_field,
                    "type": "nominal",
                    "scale": {"scheme": scheme},
                }
    elif chart_type in (ChartType.LINE, ChartType.AREA, ChartType.SCATTER):
        color_enc = encoding.get("color")
        if isinstance(color_enc, dict) and color_enc.get("field"):
            color_enc = copy.deepcopy(color_enc)
            color_enc["scale"] = {"scheme": scheme}
            encoding["color"] = color_enc
        else:
            encoding["color"] = {"value": primary_color}

    return styled
