"""Tests for LiteLLM HTTP error mapping."""

from __future__ import annotations

import litellm
from seal_core.llm.http_errors import (
    _CLIENT_LLM_AUTH,
    _CLIENT_LLM_BAD_REQUEST,
    find_litellm_exception,
    llm_http_error,
)


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
