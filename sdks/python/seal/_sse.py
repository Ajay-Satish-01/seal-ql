"""Minimal SSE parser for /v1/chat streaming responses."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Literal, TypedDict

if TYPE_CHECKING:
    from collections.abc import Iterator


ScopeSource = Literal["heuristic", "llm", "limits", "disabled"]


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
                return {"type": "meta", "data": json.loads(data_line)}
            except json.JSONDecodeError:
                return None

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
