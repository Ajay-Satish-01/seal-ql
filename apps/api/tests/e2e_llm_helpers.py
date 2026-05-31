"""Shared helpers for live LLM E2E tests (pytest + SDK).

Skip when the provider/model is unavailable (quota, 5xx, timeouts).
Fail on auth regressions, unexpected 4xx scope errors, or invalid 200 bodies.
"""

from __future__ import annotations

import warnings
from typing import Any

import pytest

_LLM_SKIP_HTTP = frozenset({429, 500, 502, 503, 504})
_LLM_SKIP_TEXT_MARKERS = (
    "ratelimit",
    "rate limit",
    "rate_limit",
    "quota",
    "resource_exhausted",
    "too many requests",
    "timeout",
    "timed out",
    "connection error",
    "connection refused",
    "litellm",
    "instructor",
    "vertexai",
    "geminiexception",
    "ollama",
    "model not found",
    "internal error occurred",
    "an internal error",
)


def _snippet(text: str, limit: int = 400) -> str:
    t = (text or "").strip()
    return t if len(t) <= limit else f"{t[:limit]}…"


def llm_unavailable_reason(
    *,
    status_code: int | None = None,
    body: str = "",
    exc: BaseException | None = None,
) -> str | None:
    """Return a human skip reason for transient LLM failures; None => treat as test failure."""
    if status_code == 401:
        return None

    if status_code in _LLM_SKIP_HTTP:
        return f"HTTP {status_code}: {_snippet(body)}"

    blob = f"{status_code or ''} {body}".lower()
    if status_code and status_code >= 400 and any(m in blob for m in _LLM_SKIP_TEXT_MARKERS):
        return _snippet(body) or f"HTTP {status_code}"

    if exc is not None:
        name = type(exc).__name__.lower()
        msg = str(exc).lower()
        if any(m in msg or m in name for m in _LLM_SKIP_TEXT_MARKERS):
            return f"{type(exc).__name__}: {_snippet(str(exc))}"

    if status_code is not None and status_code >= 500:
        return f"HTTP {status_code}: {_snippet(body)}"

    return None


def skip_if_llm_unavailable(
    *,
    status_code: int | None = None,
    body: str = "",
    exc: BaseException | None = None,
) -> None:
    reason = llm_unavailable_reason(status_code=status_code, body=body, exc=exc)
    if reason is not None:
        warnings.warn(
            f"Skipping LLM E2E (provider/model unavailable): {reason}",
            UserWarning,
            stacklevel=2,
        )
        pytest.skip(f"LLM unavailable: {reason}")


def assert_chat_json_body(body: dict[str, Any]) -> None:
    """Strict checks when chat returns HTTP 200."""
    assert body.get("session_id"), "expected session_id in 200 chat response"
    message = body.get("message")
    assert message and str(message).strip(), "expected non-empty message in 200 chat response"


def assert_query_json_body(data: dict[str, Any]) -> None:
    """Strict checks when query returns HTTP 200."""
    sql = data.get("sql")
    assert sql and str(sql).strip(), "expected non-empty sql in 200 query response"
    results = data.get("results")
    assert isinstance(results, list) and len(results) > 0, "expected at least one result row"
    metadata = data.get("metadata") or {}
    row_count = metadata.get("row_count", len(results))
    assert row_count > 0, "expected row_count > 0"
