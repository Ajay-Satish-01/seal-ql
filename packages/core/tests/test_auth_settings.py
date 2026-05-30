"""Tests for API authentication settings."""

from __future__ import annotations

from seal_core.settings import Settings


def test_auth_required_without_key_returns_error() -> None:
    settings = Settings.model_construct(auth_required=True, api_key=None)
    errors = settings.validate_auth_configuration()
    assert len(errors) == 1
    assert "SEAL_API_KEY" in errors[0]


def test_auth_required_with_key_is_valid() -> None:
    settings = Settings(auth_required=True, api_key="secret")
    assert settings.validate_auth_configuration() == []


def test_empty_api_key_normalized_to_none() -> None:
    settings = Settings(api_key="   ")
    assert settings.api_key is None
    assert settings.validate_auth_configuration() == []


def test_placeholder_key_rejected_when_auth_required() -> None:
    settings = Settings.model_construct(
        auth_required=True,
        api_key="dev-local-change-me",
        dev_mode=False,
        disable_public_docs=None,
    )
    errors = settings.validate_auth_configuration()
    assert len(errors) == 1
    assert "placeholder" in errors[0].lower()


def test_placeholder_key_rejected_without_dev_mode() -> None:
    settings = Settings.model_construct(
        auth_required=False,
        api_key="dev-local-change-me",
        dev_mode=False,
        disable_public_docs=None,
    )
    errors = settings.validate_auth_configuration()
    assert len(errors) == 1


def test_placeholder_key_allowed_in_dev_mode() -> None:
    settings = Settings.model_construct(
        auth_required=False,
        api_key="dev-local-change-me",
        dev_mode=True,
        disable_public_docs=None,
    )
    assert settings.validate_auth_configuration() == []


def test_dev_mode_does_not_override_auth_required() -> None:
    settings = Settings.model_construct(
        auth_required=True,
        api_key="dev-local-change-me",
        dev_mode=True,
        disable_public_docs=None,
    )
    errors = settings.validate_auth_configuration()
    assert len(errors) == 1
    assert "placeholder" in errors[0].lower()


def test_disable_public_docs_defaults_to_auth_required() -> None:
    required = Settings.model_construct(
        auth_required=True,
        api_key="a" * 32,
        disable_public_docs=None,
    )
    assert required.effective_disable_public_docs() is True

    optional = Settings.model_construct(
        auth_required=False,
        api_key="a" * 32,
        disable_public_docs=None,
    )
    assert optional.effective_disable_public_docs() is False

    explicit = Settings.model_construct(
        auth_required=True,
        api_key="a" * 32,
        disable_public_docs=False,
    )
    assert explicit.effective_disable_public_docs() is False
