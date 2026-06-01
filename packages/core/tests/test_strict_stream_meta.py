"""Tests for strict seal.meta validation setting."""

from __future__ import annotations

import pytest
from seal_core.pipeline.validate_metadata import (
    InvalidChatMetadataError,
    InvalidQueryMetadataError,
    InvalidStreamMetaError,
    enforce_nested_chat_metadata,
    enforce_query_metadata,
    enforce_stream_meta_validation,
)
from seal_core.settings import _load_settings, get_settings


def test_strict_stream_meta_validation_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRICT_STREAM_META_VALIDATION", "true")
    _load_settings.cache_clear()
    try:
        assert get_settings().strict_stream_meta_validation is True
        with pytest.raises(InvalidStreamMetaError, match="invalid seal.meta"):
            enforce_stream_meta_validation(
                {"session_id": "s1", "sql": "SELECT 1", "used_sql": True}
            )
    finally:
        _load_settings.cache_clear()


def test_strict_metadata_validation_env_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRICT_STREAM_META_VALIDATION", raising=False)
    monkeypatch.setenv("STRICT_METADATA_VALIDATION", "true")
    _load_settings.cache_clear()
    try:
        assert get_settings().strict_stream_meta_validation is True
    finally:
        _load_settings.cache_clear()


def test_strict_query_metadata_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRICT_STREAM_META_VALIDATION", "true")
    _load_settings.cache_clear()
    try:
        with pytest.raises(InvalidQueryMetadataError, match="invalid query metadata"):
            enforce_query_metadata({"database_id": "default", "used_sql": True})
    finally:
        _load_settings.cache_clear()


def test_strict_nested_chat_metadata_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRICT_STREAM_META_VALIDATION", "true")
    _load_settings.cache_clear()
    try:
        with pytest.raises(InvalidChatMetadataError, match="invalid chat metadata"):
            enforce_nested_chat_metadata({"used_sql": True}, sql="SELECT 1")
    finally:
        _load_settings.cache_clear()


def test_strict_stream_meta_validation_off_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("STRICT_STREAM_META_VALIDATION", raising=False)
    monkeypatch.delenv("STRICT_METADATA_VALIDATION", raising=False)
    _load_settings.cache_clear()
    try:
        assert get_settings().strict_stream_meta_validation is False
        enforce_stream_meta_validation(
            {
                "session_id": "s1",
                "sql": "SELECT 1",
                "used_sql": True,
                "enhancement": {"enabled": True, "applied": []},
            }
        )
    finally:
        _load_settings.cache_clear()
