"""Unit tests for live LLM E2E skip/probe helpers."""

from __future__ import annotations

import httpx
import pytest
from seal.exceptions import SealConnectionError
from tests.e2e_llm_helpers import llm_unavailable_reason, probe_live_chat, probe_live_llm


def test_llm_unavailable_reason_detects_timeout_in_cause_chain() -> None:
    cause = httpx.ReadTimeout("The read operation timed out")
    exc = SealConnectionError("Cannot connect to http://localhost:8000")
    exc.__cause__ = cause

    reason = llm_unavailable_reason(exc=exc)

    assert reason is not None
    assert "ReadTimeout" in reason


def test_llm_unavailable_reason_detects_timeout_message() -> None:
    exc = SealConnectionError("Request to http://localhost:8000 timed out")

    reason = llm_unavailable_reason(exc=exc)

    assert reason is not None
    assert "timed out" in reason.lower()


def test_llm_unavailable_reason_ignores_auth_failure() -> None:
    assert llm_unavailable_reason(status_code=401, body="Unauthorized") is None


def test_llm_unavailable_reason_detects_model_not_available() -> None:
    reason = llm_unavailable_reason(
        status_code=503,
        body="Model not available for this deployment",
    )
    assert reason is not None
    assert "503" in reason


def test_probe_live_llm_skips_on_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        status_code = 500
        text = '{"detail":"An internal error occurred."}'

    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, *args: object, **kwargs: object) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr("tests.e2e_llm_helpers.httpx.Client", FakeClient)

    reason = probe_live_llm(base_url="http://localhost:8000", api_key="test")

    assert reason is not None
    assert "500" in reason


def test_probe_live_chat_skips_on_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        status_code = 429
        text = '{"detail":"Rate limit exceeded"}'

    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, *args: object, **kwargs: object) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr("tests.e2e_llm_helpers.httpx.Client", FakeClient)

    reason = probe_live_chat(base_url="http://localhost:8000", api_key="test")

    assert reason is not None
    assert "429" in reason
