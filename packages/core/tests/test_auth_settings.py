"""Tests for API authentication settings."""

from __future__ import annotations

import pytest
from seal_core.settings import Settings


def test_missing_api_key_returns_error() -> None:
    settings = Settings.model_construct(api_key=None)
    errors = settings.validate_auth_configuration()
    assert len(errors) == 1
    assert "SEAL_API_KEY" in errors[0]


def test_valid_api_key_passes() -> None:
    settings = Settings.model_construct(
        api_key="seal-pytest-api-key-0123456789abcdef0123456789abcdef",
        disable_public_docs=None,
    )
    assert settings.validate_auth_configuration() == []


def test_empty_api_key_normalized_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEAL_API_KEY", raising=False)
    settings = Settings(api_key="   ", _env_file=None)
    assert settings.api_key is None
    assert settings.validate_auth_configuration() != []


def test_placeholder_key_rejected() -> None:
    settings = Settings.model_construct(
        api_key="dev-local-change-me",
        disable_public_docs=None,
    )
    errors = settings.validate_auth_configuration()
    assert len(errors) == 1
    assert "placeholder" in errors[0].lower()


def test_disable_public_docs_defaults_to_false() -> None:
    settings = Settings.model_construct(
        api_key="a" * 32,
        disable_public_docs=None,
    )
    assert settings.effective_disable_public_docs() is False

    explicit = Settings.model_construct(
        api_key="a" * 32,
        disable_public_docs=True,
    )
    assert explicit.effective_disable_public_docs() is True
