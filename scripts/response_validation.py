"""Validate QueryResponse JSON shape and chart plottability."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
_CORE = _ROOT / "packages" / "core"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from seal_core.pipeline.validate_metadata import (  # noqa: E402
    validate_execution_fields,
    validate_nested_chat_metadata,
    validate_stream_meta_event,
    validate_suggested_queries,
)

VEGA_CHART_TYPES = frozenset({"bar", "line", "pie", "scatter", "area"})
NATIVE_CHART_TYPES = frozenset({"table", "metric_card"})
CHART_TYPES = VEGA_CHART_TYPES | NATIVE_CHART_TYPES
REQUIRED_TOP = frozenset({"sql", "columns", "results", "metadata"})
CHAT_REQUIRED_TOP = frozenset({"session_id", "message", "metadata"})


def validate_query_response(data: dict[str, Any]) -> list[str]:
    """Validate top-level QueryResponse fields."""
    errors: list[str] = []
    missing = REQUIRED_TOP - set(data.keys())
    if missing:
        errors.append(f"Missing top-level keys: {sorted(missing)}")

    if "sql" in data and not isinstance(data["sql"], str):
        errors.append("sql must be a string")

    columns = data.get("columns")
    if columns is not None and not isinstance(columns, list):
        errors.append("columns must be an array")
    elif isinstance(columns, list):
        for i, col in enumerate(columns):
            if not isinstance(col, dict) or "name" not in col or "type" not in col:
                errors.append(f"columns[{i}] must have name and type")

    results = data.get("results")
    if results is not None and not isinstance(results, list):
        errors.append("results must be an array")
    elif isinstance(results, list) and results and not isinstance(results[0], dict):
        errors.append("results items must be objects")

    if "chart" in data:
        chart = data["chart"]
        if chart is not None:
            errors.extend(validate_chart_object(chart, data.get("results") or []))

    meta = data.get("metadata")
    if meta is not None and not isinstance(meta, dict):
        errors.append("metadata must be an object")
    elif isinstance(meta, dict):
        sql_value = data.get("sql")
        require_meta = isinstance(sql_value, str) and bool(sql_value.strip())
        errors.extend(validate_execution_fields(meta, require_when_sql=require_meta))

    return errors


def validate_chat_response(data: dict[str, Any]) -> list[str]:
    """Validate top-level ChatResponse fields and metadata shape."""
    errors: list[str] = []
    missing = CHAT_REQUIRED_TOP - set(data.keys())
    if missing:
        errors.append(f"Missing top-level keys: {sorted(missing)}")

    if "session_id" in data and not isinstance(data["session_id"], str):
        errors.append("session_id must be a string")
    if "message" in data and not isinstance(data["message"], str):
        errors.append("message must be a string")

    meta = data.get("metadata")
    if meta is not None and not isinstance(meta, dict):
        errors.append("metadata must be an object")
    elif isinstance(meta, dict):
        sql_value = data.get("sql")
        require_meta = isinstance(sql_value, str) and bool(sql_value.strip())
        errors.extend(validate_nested_chat_metadata(meta, sql_at_top_level=require_meta))
        if meta.get("refusal") is True and "suggested_queries" in meta:
            errors.extend(validate_suggested_queries(meta.get("suggested_queries")))

    columns = data.get("columns")
    if columns is not None and not isinstance(columns, list):
        errors.append("columns must be an array or null")
    elif isinstance(columns, list):
        for i, col in enumerate(columns):
            if not isinstance(col, dict) or "name" not in col or "type" not in col:
                errors.append(f"columns[{i}] must have name and type")

    return errors


def validate_chat_stream_meta(data: dict[str, Any]) -> list[str]:
    """Validate flat JSON on the ``data:`` line of a ``seal.meta`` SSE event."""
    return validate_stream_meta_event(data)


def validate_chart_object(chart: Any, results: list[dict[str, Any]]) -> list[str]:
    """Validate chart object structure and type-specific plottability."""
    errors: list[str] = []
    if not isinstance(chart, dict):
        errors.append("chart must be an object or null")
        return errors

    ct = chart.get("chart_type")
    if ct not in CHART_TYPES:
        errors.append(f"chart.chart_type invalid: {ct!r}")
        return errors

    if "vega_lite_spec" not in chart:
        errors.append("chart missing vega_lite_spec")
    if "metadata" not in chart:
        errors.append("chart missing metadata")

    spec = chart.get("vega_lite_spec")
    meta = chart.get("metadata") or {}

    if ct in NATIVE_CHART_TYPES:
        if spec:
            errors.append(f"chart_type {ct!r} must have empty vega_lite_spec")
        if ct == "metric_card" and not results:
            errors.append("metric_card requires at least one result row")
        if ct == "metric_card":
            y_field = meta.get("y_field")
            if y_field and results and y_field not in results[0]:
                errors.append(f"metric_card y_field {y_field!r} not in first result row")
        return errors

    errors.extend(_validate_vega_spec(ct, spec, meta, results))
    return errors


def _validate_vega_spec(
    chart_type: str,
    spec: Any,
    meta: dict[str, Any],
    results: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(spec, dict) or not spec:
        errors.append(f"chart_type {chart_type!r} requires non-empty vega_lite_spec")
        return errors

    if spec.get("$schema") != "https://vega.github.io/schema/vega-lite/v5.json":
        errors.append("vega_lite_spec missing or wrong $schema")

    data = spec.get("data")
    if not isinstance(data, dict) or "values" not in data:
        errors.append("vega_lite_spec missing data.values")
    elif not isinstance(data["values"], list):
        errors.append("vega_lite_spec data.values must be a list")
    elif len(data["values"]) != len(results):
        errors.append(
            f"data.values length ({len(data['values'])}) != results length ({len(results)})"
        )

    enc = spec.get("encoding")
    if chart_type == "pie":
        if not isinstance(enc, dict) or "theta" not in enc or "color" not in enc:
            errors.append("pie chart missing encoding.theta or encoding.color")
        else:
            theta = enc["theta"] if isinstance(enc["theta"], dict) else {}
            color = enc["color"] if isinstance(enc["color"], dict) else {}
            yf = theta.get("field")
            xf = color.get("field")
            if meta.get("x_field") != xf:
                errors.append(
                    f"metadata.x_field {meta.get('x_field')!r} != encoding.color.field {xf!r}"
                )
            if meta.get("y_field") != yf:
                errors.append(
                    f"metadata.y_field {meta.get('y_field')!r} != encoding.theta.field {yf!r}"
                )
    else:
        if not isinstance(enc, dict) or "x" not in enc or "y" not in enc:
            errors.append(f"{chart_type} chart missing encoding.x or encoding.y")
        else:
            x_enc = enc["x"] if isinstance(enc["x"], dict) else {}
            y_enc = enc["y"] if isinstance(enc["y"], dict) else {}
            xf = x_enc.get("field")
            yf = y_enc.get("field")
            if meta.get("x_field") != xf:
                errors.append(
                    f"metadata.x_field {meta.get('x_field')!r} != encoding.x.field {xf!r}"
                )
            if meta.get("y_field") != yf:
                errors.append(
                    f"metadata.y_field {meta.get('y_field')!r} != encoding.y.field {yf!r}"
                )

    if not spec.get("mark"):
        errors.append("vega_lite_spec missing mark")

    return errors
