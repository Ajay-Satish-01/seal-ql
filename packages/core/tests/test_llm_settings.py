"""Tests for LLM settings (OLLAMA_PROFILE-driven, via Pydantic Settings)."""

from __future__ import annotations

import pytest
from seal_core.llm import client as llm_client
from seal_core.llm.client import get_api_base, get_api_key, get_model
from seal_core.settings import Settings, clear_settings_cache, get_settings


def _clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate tests from CI/docker env and from a developer's local .env file."""
    # Disable .env loading so on-disk values can't leak into Settings under test.
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for name in (
        "OLLAMA_PROFILE",
        "LLM_MODEL",
        "LLM_BASE_URL",
        "LLM_API_KEY",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    clear_settings_cache()


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    llm_client._config_validated = False
    yield
    clear_settings_cache()
    llm_client._config_validated = False


def test_ollama_profile_disabled_uses_cloud_routing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_PROFILE", "disabled")
    monkeypatch.setenv("LLM_MODEL", "gemini/gemini-1.5-flash")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    clear_settings_cache()

    settings = get_settings()
    assert settings.use_cloud_llm()
    assert settings.llm_mode_label() == "cloud"
    assert get_api_base() is None
    assert get_api_key() == "test-key"
    assert get_model() == "gemini/gemini-1.5-flash"
    assert not settings.collect_llm_configuration_warnings()


def test_local_ollama_when_profile_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_PROFILE", "default")
    monkeypatch.setenv("LLM_MODEL", "llama3.2:1b")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    settings = get_settings()
    assert not settings.use_cloud_llm()
    assert get_api_base() == "http://ollama:11434"
    assert get_api_key() is None
    assert get_model() == "ollama/llama3.2:1b"


def test_gemini_api_key_counts_for_cloud(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_PROFILE", "disabled")
    monkeypatch.setenv("LLM_MODEL", "gemini/gemini-1.5-flash")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")

    settings = get_settings()
    assert settings.has_cloud_api_credentials()
    assert not settings.collect_llm_configuration_warnings()


def test_warn_cloud_model_without_disabled_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_PROFILE", "default")
    monkeypatch.setenv("LLM_MODEL", "gemini/gemini-1.5-flash")

    warnings = get_settings().collect_llm_configuration_warnings()
    assert any("OLLAMA_PROFILE" in w and "disabled" in w for w in warnings)


def test_warn_ollama_model_with_disabled_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_PROFILE", "disabled")
    monkeypatch.setenv("LLM_MODEL", "ollama/llama3.2:1b")
    monkeypatch.setenv("LLM_API_KEY", "key")

    warnings = get_settings().collect_llm_configuration_warnings()
    assert any("ollama" in w.lower() for w in warnings)


def test_warn_unknown_ollama_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_PROFILE", "staging")
    monkeypatch.setenv("LLM_MODEL", "ollama/llama3.2:1b")

    warnings = get_settings().collect_llm_configuration_warnings()
    assert any("not recognized" in w for w in warnings)


def test_warn_cloud_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_PROFILE", "disabled")
    monkeypatch.setenv("LLM_MODEL", "gemini/gemini-1.5-flash")
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    clear_settings_cache()

    warnings = get_settings().collect_llm_configuration_warnings()
    assert any("no API key" in w for w in warnings)
