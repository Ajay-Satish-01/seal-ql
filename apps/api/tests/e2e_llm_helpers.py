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
    "model not available",
    "model unavailable",
    "no healthy upstream",
    "service unavailable",
    "overloaded",
    "internal error occurred",
    "an internal error",
)

_SCHEMA_TABLE_CLARIFY_MARKERS: tuple[str, ...] = (
    "which table or area",
    "which table",
    "table or area",
    "available schema",
    "schema area",
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


def _probe_live_route(
    *,
    base_url: str,
    path: str,
    payload: dict[str, Any],
    api_key: str | None = None,
    timeout: float = _DEFAULT_PROBE_TIMEOUT,
) -> str | None:
    """Return a skip reason when an LLM-backed route is not viable."""
    headers: dict[str, str] = {}
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        with httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
        ) as client:
            response = client.post(path, json=payload)
    except httpx.RequestError as exc:
        return llm_unavailable_reason(exc=exc) or f"{type(exc).__name__}: {_snippet(str(exc))}"

    if response.status_code == 401:
        return None
    return llm_unavailable_reason(status_code=response.status_code, body=response.text)


def probe_live_llm(
    *,
    base_url: str,
    api_key: str | None = None,
    timeout: float = _DEFAULT_PROBE_TIMEOUT,
) -> str | None:
    """Return a skip reason when /v1/query is not viable; None when LLM path looks healthy."""
    return _probe_live_route(
        base_url=base_url,
        path="/v1/query",
        payload={"query": "How many tables are in the database?"},
        api_key=api_key,
        timeout=timeout,
    )


def probe_live_chat(
    *,
    base_url: str,
    api_key: str | None = None,
    timeout: float = _DEFAULT_PROBE_TIMEOUT,
) -> str | None:
    """Return a skip reason when /v1/chat is not viable; None when LLM path looks healthy."""
    return _probe_live_route(
        base_url=base_url,
        path="/v1/chat",
        payload={
            "message": "Name one table in the database.",
            "stream": False,
            "include_charts": False,
        },
        api_key=api_key,
        timeout=timeout,
    )


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


def assert_not_refusal(body: dict[str, Any]) -> None:
    """Chat/query responses must not be guardrails refusals."""
    metadata = body.get("metadata") or {}
    assert not metadata.get("refusal"), f"unexpected refusal: {body.get('message')!r}"


def assert_no_schema_table_clarification(body: dict[str, Any]) -> None:
    """Reasoning must not ask the user to pick tables or schema areas."""
    reasoning = (body.get("metadata") or {}).get("reasoning") or {}
    questions = reasoning.get("clarifying_questions") or []
    message = str(body.get("message") or "")
    combined = f"{' '.join(questions)} {message}".lower()
    for marker in _SCHEMA_TABLE_CLARIFY_MARKERS:
        assert marker not in combined, f"unexpected schema/table clarification prompt: {combined!r}"


def post_chat_json(
    client: httpx.Client,
    *,
    message: str,
    session_id: str | None = None,
    messages: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """POST /v1/chat (non-streaming) with shared LLM skip handling."""
    payload: dict[str, Any] = {
        "message": message,
        "stream": False,
        "include_charts": False,
    }
    if session_id:
        payload["session_id"] = session_id
    if messages:
        payload["messages"] = messages
    try:
        return client.post("/v1/chat", json=payload, headers=headers)
    except httpx.RequestError as exc:
        skip_if_llm_unavailable(exc=exc)
        raise


def assert_chat_response_ok(response: httpx.Response) -> dict[str, Any]:
    """Apply LLM skip rules and return parsed chat JSON on HTTP 200."""
    assert response.status_code != 401, response.text
    skip_if_llm_unavailable(status_code=response.status_code, body=response.text)
    if response.status_code == 400:
        pytest.fail(f"Unexpected 400 from chat: {response.text}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert_chat_json_body(body)
    return body


def assert_query_response_ok(response: httpx.Response) -> dict[str, Any]:
    """Apply LLM skip rules and return parsed query JSON on HTTP 200."""
    assert response.status_code != 401, response.text
    skip_if_llm_unavailable(status_code=response.status_code, body=response.text)
    detail = ""
    try:
        detail = str(response.json().get("detail", ""))
    except Exception:
        detail = response.text
    if response.status_code == 400 and "out_of_scope" in detail:
        pytest.fail(f"Benign query incorrectly marked out of scope: {response.text}")
    if response.status_code == 400:
        pytest.fail(f"Unexpected 400 from query: {response.text}")
    assert response.status_code == 200, response.text
    body = response.json()
    return body
