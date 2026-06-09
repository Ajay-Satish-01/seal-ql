"""Shared rate-limit detection (markers sourced from config/rate_limit_markers.json)."""

from __future__ import annotations

import json
from functools import lru_cache


def _read_markers_json() -> str:
    # seal:python-sdk-markers-read-begin
    from pathlib import Path

    return Path(__file__).with_name("rate_limit_markers.json").read_text(encoding="utf-8")
    # seal:python-sdk-markers-read-end


@lru_cache(maxsize=1)
def _config() -> dict[str, object]:
    data = json.loads(_read_markers_json())
    if not isinstance(data, dict):
        msg = "rate_limit_markers.json must be an object"
        raise TypeError(msg)
    return data


def rate_limit_user_message() -> str:
    """Client-facing message when the LLM provider throttles requests."""
    message = _config().get("user_message")
    if not isinstance(message, str) or not message.strip():
        msg = "rate_limit_markers.json must define a non-empty user_message"
        raise ValueError(msg)
    return message


def rate_limit_markers() -> tuple[str, ...]:
    """Lowercase substring markers for provider throttling errors."""
    raw = _config().get("markers")
    if not isinstance(raw, list):
        msg = "rate_limit_markers.json must define a markers array"
        raise TypeError(msg)
    markers = tuple(str(item).strip().lower() for item in raw if str(item).strip())
    if not markers:
        msg = "rate_limit_markers.json markers must not be empty"
        raise ValueError(msg)
    return markers


def looks_like_rate_limit_text(text: str) -> bool:
    """True when free-text (exception message, API detail) indicates throttling."""
    lower = text.lower()
    return any(marker in lower for marker in rate_limit_markers())


def is_rate_limit_http(status: int, text: str) -> bool:
    """True for keyword matches or Seal's empty-body HTTP 503 throttling response."""
    return looks_like_rate_limit_text(text) or (status == 503 and not text.strip())
