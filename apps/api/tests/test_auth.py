"""Tests for API key authentication."""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from seal_core.settings import Settings, clear_settings_cache, get_settings
from tests.factory import build_client
from tests.shared import TEST_API_KEY, enable_trust_explainability

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


# ---------------------------------------------------------------------------
# Startup / configuration
# ---------------------------------------------------------------------------


def test_lifespan_fails_with_placeholder_key(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SEAL_API_KEY", "replace-me-with-openssl-rand-hex-32")
    monkeypatch.setenv("SEAL_DEV_MODE", "false")
    clear_settings_cache()

    with (
        pytest.raises(RuntimeError, match="placeholder"),
        build_client(monkeypatch, mock_dependencies=False),
    ):
        pass

    clear_settings_cache()


def test_lifespan_fails_without_key(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("SEAL_API_KEY", raising=False)
    clear_settings_cache()

    with (
        pytest.raises(RuntimeError, match="SEAL_API_KEY"),
        build_client(monkeypatch, mock_dependencies=False),
    ):
        pass

    clear_settings_cache()


def test_placeholder_key_always_rejected() -> None:
    settings = Settings.model_construct(
        api_key="dev-local-change-me",
        disable_public_docs=None,
    )
    errors = settings.validate_auth_configuration()
    assert len(errors) == 1
    assert "placeholder" in errors[0].lower()


def test_empty_api_key_treated_as_missing(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SEAL_API_KEY", "   ")
    clear_settings_cache()

    with (
        pytest.raises(RuntimeError, match="SEAL_API_KEY"),
        build_client(monkeypatch, mock_dependencies=False),
    ):
        pass

    clear_settings_cache()


# ---------------------------------------------------------------------------
# Protected routes (auth enabled)
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_client(monkeypatch: MonkeyPatch) -> Generator[TestClient, None, None]:
    client = build_client(
        monkeypatch,
        SEAL_API_KEY=TEST_API_KEY,
        SEAL_DEV_MODE="true",
    )
    yield client
    client.close()
    clear_settings_cache()


def test_health_is_public(auth_client: TestClient) -> None:
    response = auth_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "trust_explainability_enabled": False,
    }


def test_health_reflects_trust_toggle_when_enabled(auth_client: TestClient, monkeypatch) -> None:
    enable_trust_explainability(monkeypatch)
    response = auth_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "trust_explainability_enabled": True,
    }


def test_schema_requires_api_key(auth_client: TestClient) -> None:
    denied = auth_client.get("/v1/schema")
    assert denied.status_code == 401
    assert denied.json()["detail"] == "Invalid or missing API key"

    ok = auth_client.get("/v1/schema", headers={"X-API-Key": TEST_API_KEY})
    assert ok.status_code == 200


def test_query_requires_api_key(auth_client: TestClient) -> None:
    denied = auth_client.post("/v1/query", json={"query": "test"})
    assert denied.status_code == 401

    ok = auth_client.post(
        "/v1/query",
        json={"query": "test"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert ok.status_code == 200


def test_invalid_api_key_rejected(auth_client: TestClient) -> None:
    response = auth_client.get("/v1/schema", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401
    assert "wrong" not in response.json()["detail"].lower()


def test_valid_key_starts(monkeypatch: MonkeyPatch) -> None:
    strong_key = "a" * 64
    with build_client(
        monkeypatch,
        SEAL_API_KEY=strong_key,
        SEAL_DEV_MODE="false",
    ) as client:
        assert client.get("/health").status_code == 200
        denied = client.get("/v1/schema")
        assert denied.status_code == 401
        assert client.get("/v1/schema", headers={"X-API-Key": strong_key}).status_code == 200


def test_compare_digest_used_for_valid_key(auth_client: TestClient) -> None:
    """Correct key must match exactly (no prefix/suffix acceptance)."""
    almost = TEST_API_KEY + "x"
    response = auth_client.get("/v1/schema", headers={"X-API-Key": almost})
    assert response.status_code == 401


def test_compare_helper_rejects_non_ascii_without_raising() -> None:
    """Non-ASCII keys must compare to False, not raise TypeError (which would 500).

    Starlette decodes raw header bytes as latin-1, so a handler can legitimately
    receive a str with codepoints that ``secrets.compare_digest`` cannot digest
    unless we encode to bytes first.
    """
    from app.security import _api_key_matches

    assert _api_key_matches("kéy-not-the-secret", TEST_API_KEY) is False
    assert _api_key_matches("🔑", TEST_API_KEY) is False
    assert _api_key_matches(None, TEST_API_KEY) is False
    assert _api_key_matches(TEST_API_KEY, None) is False
    assert _api_key_matches(TEST_API_KEY, TEST_API_KEY) is True


def test_misconfigured_auth_returns_503(monkeypatch: MonkeyPatch) -> None:
    """Runtime guard when the key was cleared after startup."""
    strong_key = "b" * 64
    with build_client(
        monkeypatch,
        SEAL_API_KEY=strong_key,
        SEAL_DEV_MODE="false",
        mock_dependencies=False,
    ) as client:
        misconfigured = get_settings().model_copy(update={"api_key": None})
        monkeypatch.setattr("app.security.get_settings", lambda: misconfigured)
        response = client.get("/v1/schema", headers={"X-API-Key": "any"})
        assert response.status_code == 503
        assert response.json()["detail"] == "API authentication is misconfigured"

    clear_settings_cache()
