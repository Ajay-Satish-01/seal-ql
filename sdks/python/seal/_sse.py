"""Minimal SSE parser for /v1/chat streaming responses."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast

if TYPE_CHECKING:
    from collections.abc import Iterator

ScopeSource = Literal["heuristic", "llm", "limits", "disabled"]

_SCOPE_SOURCES = frozenset({"heuristic", "llm", "limits", "disabled"})
_VECTOR_SKIPPED_REASONS = frozenset({"non_default_database", "vector_store_disabled"})
_UNAVAILABLE_REASONS = frozenset({"orchestrator_unavailable"})


class ChatStreamScope(TypedDict, total=False):
    in_scope: bool
    reason: str
    source: ScopeSource


class ChatStreamMeta(TypedDict, total=False):
    session_id: str
    sources: list[str]
    sql: str | None
    results: list[dict[str, Any]] | None
    columns: list[dict[str, Any]] | None
    chart: dict[str, Any] | None
    database_id: str
    row_count: int
    execution_time_ms: float
    truncated: bool
    warnings: list[str]
    repair_attempts: int
    used_sql: bool
    enhancement: dict[str, Any]
    scope: ChatStreamScope
    refusal: bool
    sql_error: bool


class ChatStreamMetaErrorEvent(TypedDict):
    type: Literal["meta_error"]
    error: str
    partial: ChatStreamMeta


class ChatStreamMetaEvent(TypedDict):
    type: Literal["meta"]
    data: ChatStreamMeta


class ChatStreamDeltaEvent(TypedDict):
    type: Literal["delta"]
    content: str


class ChatStreamDoneEvent(TypedDict):
    type: Literal["done"]


ChatStreamEvent = (
    ChatStreamMetaEvent | ChatStreamMetaErrorEvent | ChatStreamDeltaEvent | ChatStreamDoneEvent
)

_EXECUTION_KEYS = frozenset(
    {
        "database_id",
        "row_count",
        "execution_time_ms",
        "truncated",
        "warnings",
        "repair_attempts",
        "used_sql",
    }
)


def _sql_present(payload: dict[str, Any]) -> bool:
    sql_value = payload.get("sql")
    return isinstance(sql_value, str) and bool(sql_value.strip())


def _requires_enhancement_block(meta: dict[str, Any]) -> bool:
    return (
        meta.get("used_sql") is True or meta.get("refusal") is True or meta.get("sql_error") is True
    )


def _partial_meta_from_raw(data: Any) -> ChatStreamMeta:
    if not isinstance(data, dict):
        return cast("ChatStreamMeta", {})
    partial: dict[str, Any] = {}
    session_id = data.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        partial["session_id"] = session_id
    database_id = data.get("database_id")
    if isinstance(database_id, str):
        partial["database_id"] = database_id
    return cast("ChatStreamMeta", partial)


def _validate_stream_meta_dict(data: dict[str, Any]) -> list[str]:
    """Mirror server ``validate_stream_meta_event`` for SDK-side parity."""
    errors: list[str] = []
    for key in ("used_sql", "refusal", "sql_error", "truncated"):
        if key in data and not isinstance(data[key], bool):
            errors.append(f"{key} must be a boolean")

    session_id = data.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        errors.append("session_id must be a non-empty string")

    if _sql_present(data):
        missing = _EXECUTION_KEYS - set(data.keys())
        if missing:
            errors.append(f"missing execution keys when sql present: {sorted(missing)}")
        database_id = data.get("database_id")
        if not isinstance(database_id, str):
            errors.append("database_id must be a string")
        elif not database_id.strip():
            errors.append("database_id must be a non-empty string")
        warnings = data.get("warnings")
        if warnings is not None and not isinstance(warnings, list):
            errors.append("warnings must be an array")
        for key in ("row_count", "repair_attempts"):
            if key in data and not isinstance(data[key], (int, float)):
                errors.append(f"{key} must be numeric")

    if _requires_enhancement_block(data):
        errors.extend(_validate_enhancement(data.get("enhancement"), required=True))
    elif data.get("enhancement") is not None:
        errors.extend(_validate_enhancement(data.get("enhancement"), required=False))

    scope = data.get("scope")
    if scope is not None:
        errors.extend(_validate_scope(scope))

    columns = data.get("columns")
    if columns is not None and not isinstance(columns, list):
        errors.append("columns must be an array or null")
    elif isinstance(columns, list):
        for i, col in enumerate(columns):
            if not isinstance(col, dict) or "name" not in col or "type" not in col:
                errors.append(f"columns[{i}] must have name and type")

    return errors


def _validate_enhancement(enh: Any, *, required: bool) -> list[str]:
    errors: list[str] = []
    if enh is None:
        if required:
            errors.append("enhancement object required")
        return errors
    if not isinstance(enh, dict):
        errors.append("enhancement must be an object")
        return errors
    if "enabled" not in enh:
        errors.append("enhancement missing enabled")
    elif not isinstance(enh["enabled"], bool):
        errors.append("enhancement.enabled must be a boolean")
    if "applied" not in enh:
        errors.append("enhancement missing applied")
    elif not isinstance(enh["applied"], list):
        errors.append("enhancement.applied must be an array")
    elif not all(isinstance(item, str) for item in enh["applied"]):
        errors.append("enhancement.applied must be an array of strings")
    vector_skipped = enh.get("vector_skipped_reason")
    if vector_skipped is not None and (
        not isinstance(vector_skipped, str) or vector_skipped not in _VECTOR_SKIPPED_REASONS
    ):
        errors.append(
            "enhancement.vector_skipped_reason must be non_default_database or "
            "vector_store_disabled"
        )
    unavailable = enh.get("unavailable_reason")
    if unavailable is not None and (
        not isinstance(unavailable, str) or unavailable not in _UNAVAILABLE_REASONS
    ):
        errors.append("enhancement.unavailable_reason must be orchestrator_unavailable")
    return errors


def _validate_scope(scope: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(scope, dict):
        errors.append("scope must be an object")
        return errors
    if "in_scope" not in scope or not isinstance(scope["in_scope"], bool):
        errors.append("scope.in_scope must be a boolean")
    reason = scope.get("reason")
    if reason is not None and not isinstance(reason, str):
        errors.append("scope.reason must be a string")
    source = scope.get("source")
    if source is None:
        errors.append("scope.source is required")
    elif not isinstance(source, str) or source not in _SCOPE_SOURCES:
        errors.append("scope.source must be heuristic, llm, limits, or disabled")
    return errors


def _try_parse_stream_meta(data: dict[str, Any]) -> tuple[ChatStreamMeta | None, str | None]:
    errors = _validate_stream_meta_dict(data)
    if errors:
        return None, "; ".join(errors)
    return cast("ChatStreamMeta", data), None


def parse_sse_stream(lines: Iterator[str]) -> Iterator[ChatStreamEvent]:
    """Parse SSE lines from an httpx streaming response."""
    event_name = ""
    data_parts: list[str] = []

    def flush() -> ChatStreamEvent | None:
        nonlocal event_name, data_parts
        if not data_parts:
            event_name = ""
            return None
        data_line = "\n".join(data_parts).strip()
        event_name_local = event_name
        event_name = ""
        data_parts = []

        if data_line == "[DONE]":
            return {"type": "done"}

        if event_name_local == "seal.meta":
            try:
                parsed = json.loads(data_line)
            except json.JSONDecodeError as exc:
                return {
                    "type": "meta_error",
                    "error": str(exc),
                    "partial": _partial_meta_from_raw({}),
                }
            if not isinstance(parsed, dict):
                return {
                    "type": "meta_error",
                    "error": "seal.meta payload must be an object",
                    "partial": _partial_meta_from_raw(parsed),
                }
            meta, err = _try_parse_stream_meta(parsed)
            if err:
                return {
                    "type": "meta_error",
                    "error": err,
                    "partial": _partial_meta_from_raw(parsed),
                }
            return {"type": "meta", "data": meta}

        try:
            payload = json.loads(data_line)
            content = payload.get("choices", [{}])[0].get("delta", {}).get("content")
            if content:
                return {"type": "delta", "content": content}
        except (json.JSONDecodeError, IndexError, AttributeError):
            return None
        return None

    for raw in lines:
        line = raw.rstrip("\r")
        if line == "":
            event = flush()
            if event is not None:
                yield event
            continue
        if line.startswith("event:"):
            event_name = line[6:].strip()
        elif line.startswith("data:"):
            data_parts.append(line[5:].strip())

    event = flush()
    if event is not None:
        yield event
