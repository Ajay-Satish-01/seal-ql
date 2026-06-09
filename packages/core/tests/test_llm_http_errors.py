"""Tests for LiteLLM HTTP error mapping."""

from __future__ import annotations

import litellm
from seal_core.llm.http_errors import (
    _CLIENT_LLM_AUTH,
    _CLIENT_LLM_BAD_REQUEST,
    _CLIENT_LLM_GENERIC,
    find_litellm_exception,
    llm_error_event_code,
    llm_http_error,
    llm_stream_error_sse,
)
from seal_core.llm.rate_limit import rate_limit_user_message


def test_maps_not_found_error() -> None:
    exc = litellm.NotFoundError(
        message="model missing",
        llm_provider="gemini",
        model="gemini/bad",
    )
    mapped = llm_http_error(exc)
    assert mapped is not None
    assert mapped[0] == 502
    assert "LLM_MODEL" in mapped[1]


def test_finds_nested_litellm_error() -> None:
    root = litellm.AuthenticationError(
        message="bad key",
        llm_provider="openai",
        model="openai/gpt-4o-mini",
    )
    try:
        raise root
    except litellm.AuthenticationError as caught:
        wrapped = RuntimeError("outer")
        wrapped.__cause__ = caught
    assert find_litellm_exception(wrapped) is root
    mapped = llm_http_error(wrapped)
    assert mapped == (502, _CLIENT_LLM_AUTH)


def test_maps_groq_decommissioned_bad_request() -> None:
    exc = litellm.BadRequestError(
        message=(
            'GroqException - {"error":{"message":"The model `llama3-8b-8192` has been '
            'decommissioned","code":"model_decommissioned"}}'
        ),
        llm_provider="groq",
        model="groq/llama3-8b-8192",
    )
    mapped = llm_http_error(exc)
    assert mapped is not None
    assert mapped[0] == 502
    assert "decommissioned" in mapped[1].lower()
    assert "LLM_MODEL" in mapped[1]


def test_maps_generic_bad_request() -> None:
    exc = litellm.BadRequestError(
        message="invalid parameter",
        llm_provider="openai",
        model="openai/gpt-4o-mini",
    )
    mapped = llm_http_error(exc)
    assert mapped == (502, _CLIENT_LLM_BAD_REQUEST)


def test_maps_missing_credentials_in_chain() -> None:
    exc = litellm.InternalServerError(
        message="Missing credentials. Please pass api_key or set OPENAI_API_KEY",
        llm_provider="openai",
        model="openai/text-embedding-3-small",
    )
    mapped = llm_http_error(exc)
    assert mapped is not None
    assert mapped[0] == 502
    assert "OPENAI_API_KEY" in mapped[1]


def test_returns_none_for_unrelated_error() -> None:
    assert llm_http_error(ValueError("nope")) is None


def test_maps_rate_limit_error() -> None:
    exc = litellm.RateLimitError(
        message="Rate limit reached for model",
        llm_provider="groq",
        model="openai/gpt-oss-120b",
    )
    mapped = llm_http_error(exc)
    assert mapped == (503, rate_limit_user_message())


def test_maps_rate_limit_wrapped_in_exception_chain() -> None:
    root = litellm.RateLimitError(
        message="Rate limit reached",
        llm_provider="groq",
        model="openai/gpt-oss-120b",
    )
    try:
        raise root
    except litellm.RateLimitError as caught:
        wrapped = RuntimeError("Instructor retry failed after 2 attempts")
        wrapped.__cause__ = caught
    mapped = llm_http_error(wrapped)
    assert mapped is not None
    assert mapped[0] == 503
    assert "Rate limited" in mapped[1]


def test_maps_internal_server_error_with_rate_limit_text() -> None:
    exc = litellm.InternalServerError(
        message="Rate limit exceeded for tokens per minute",
        llm_provider="groq",
        model="openai/gpt-oss-120b",
    )
    mapped = llm_http_error(exc)
    assert mapped is not None
    assert mapped[0] == 503
    assert "Rate limited" in mapped[1]


def test_maps_internal_server_error_to_generic_502() -> None:
    exc = litellm.InternalServerError(
        message="upstream service unavailable",
        llm_provider="openai",
        model="openai/gpt-4o-mini",
    )
    mapped = llm_http_error(exc)
    assert mapped == (502, _CLIENT_LLM_GENERIC)


def test_bad_request_with_rate_limit_text_stays_502_not_rate_limit_code() -> None:
    exc = litellm.BadRequestError(
        message="rate limit exceeded for this model tier",
        llm_provider="openai",
        model="openai/gpt-4o-mini",
    )
    mapped = llm_http_error(exc)
    assert mapped is not None
    assert mapped[0] == 502
    frame = llm_stream_error_sse(exc)
    assert '"code": "llm_error"' in frame
    assert llm_error_event_code(mapped) == "llm_error"


def test_stream_error_sse_for_rate_limit() -> None:
    exc = litellm.RateLimitError(
        message="Rate limit reached",
        llm_provider="groq",
        model="openai/gpt-oss-120b",
    )
    frame = llm_stream_error_sse(exc)
    assert frame.startswith("event: seal.error\n")
    assert '"code": "rate_limit"' in frame
    assert "Rate limited" in frame


def test_stream_error_sse_reuses_precomputed_mapping() -> None:
    exc = litellm.RateLimitError(
        message="Rate limit reached",
        llm_provider="groq",
        model="openai/gpt-oss-120b",
    )
    mapped = llm_http_error(exc)
    assert mapped is not None
    frame = llm_stream_error_sse(exc, mapped=mapped)
    assert '"code": "rate_limit"' in frame
