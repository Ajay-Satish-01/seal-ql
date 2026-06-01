"""Shared helpers for live LLM E2E tests (pytest + SDK).

Skip when the provider/model is unavailable (quota, 5xx, timeouts).
Fail on auth regressions, unexpected 4xx scope errors, or invalid 200 bodies.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterator
from typing import Any

import httpx
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
    "readtimeout",
    "connecttimeout",
    "connection error",
    "connection refused",
    "cannot connect",
    "litellm",
    "instructor",
    "vertexai",
    "geminiexception",
    "ollama",
    "model not found",
    "internal error occurred",
    "an internal error",
)

_DEFAULT_PROBE_TIMEOUT = 60.0


def _snippet(text: str, limit: int = 400) -> str:
    t = (text or "").strip()
    return t if len(t) <= limit else f"{t[:limit]}…"


def _iter_exception_chain(exc: BaseException | None) -> Iterator[BaseException]:
    seen: set[int] = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        yield exc
        exc = exc.__cause__ or exc.__context__


def _is_timeout_exception(exc: BaseException) -> bool:
    if isinstance(exc, TimeoutError | httpx.TimeoutException):
        return True
    name = type(exc).__name__.lower()
    return name.endswith("timeout") or name == "timeouterror"


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
        chain = list(_iter_exception_chain(exc))
        for link in chain:
            if _is_timeout_exception(link):
                return f"{type(link).__name__}: {_snippet(str(link))}"
        for link in chain:
            name = type(link).__name__.lower()
            msg = str(link).lower()
            if any(m in msg or m in name for m in _LLM_SKIP_TEXT_MARKERS):
                return f"{type(link).__name__}: {_snippet(str(link))}"

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


def probe_live_llm(
    *,
    base_url: str,
    api_key: str | None = None,
    timeout: float = _DEFAULT_PROBE_TIMEOUT,
) -> str | None:
    """Return a skip reason when /v1/query is not viable; None when LLM path looks healthy."""
    headers: dict[str, str] = {}
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        with httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
        ) as client:
            response = client.post(
                "/v1/query",
                json={"query": "How many tables are in the database?"},
            )
    except httpx.RequestError as exc:
        return llm_unavailable_reason(exc=exc) or f"{type(exc).__name__}: {_snippet(str(exc))}"

    if response.status_code == 401:
        return None
    return llm_unavailable_reason(status_code=response.status_code, body=response.text)


def assert_chat_json_body(body: dict[str, Any]) -> None:
    """Strict checks when chat returns HTTP 200."""
    assert body.get("session_id"), "expected session_id in 200 chat response"
    message = body.get("message")
    assert message and str(message).strip(), "expected non-empty message in 200 chat response"
    if body.get("sql"):
        metadata = body.get("metadata") or {}
        assert metadata.get("database_id"), "expected metadata.database_id when sql present"
        assert "row_count" in metadata, "expected metadata.row_count when sql present"
        assert "repair_attempts" in metadata, "expected metadata.repair_attempts when sql present"
        enhancement = metadata.get("enhancement") or {}
        assert "enabled" in enhancement, "expected metadata.enhancement.enabled when sql present"
        assert "applied" in enhancement, "expected metadata.enhancement.applied when sql present"


def assert_query_json_body(data: dict[str, Any]) -> None:
    """Strict checks when query returns HTTP 200."""
    sql = data.get("sql")
    assert sql and str(sql).strip(), "expected non-empty sql in 200 query response"
    results = data.get("results")
    assert isinstance(results, list) and len(results) > 0, "expected at least one result row"
    metadata = data.get("metadata") or {}
    row_count = metadata.get("row_count", len(results))
    assert row_count > 0, "expected row_count > 0"
