"""Tests for shared rate-limit marker helpers."""

from __future__ import annotations

from seal_core.llm.rate_limit import (
    is_rate_limit_http,
    looks_like_rate_limit_text,
    rate_limit_markers,
    rate_limit_user_message,
)


def test_rate_limit_markers_loaded() -> None:
    markers = rate_limit_markers()
    assert "rate limit" in markers
    assert "tokens per minute" in markers


def test_looks_like_rate_limit_text() -> None:
    assert looks_like_rate_limit_text("Groq RateLimitError: rate limit exceeded")
    assert looks_like_rate_limit_text("tokens per minute limit hit")
    assert not looks_like_rate_limit_text("Service temporarily unavailable")


def test_is_rate_limit_http_empty_503() -> None:
    assert is_rate_limit_http(503, "")
    assert not is_rate_limit_http(503, "database unavailable")


def test_user_message_non_empty() -> None:
    assert "Rate limited" in rate_limit_user_message()
