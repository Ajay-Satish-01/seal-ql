"""Session store factory tests."""

from __future__ import annotations

import pytest
from seal_core.chat.session import InMemorySessionStore, create_session_store
from seal_core.chat.session.factory import collect_chat_session_store_configuration_errors
from seal_core.settings import Settings, clear_settings_cache


def _isolated_settings(monkeypatch: pytest.MonkeyPatch, **env: str) -> Settings:
    keys = (
        "CHAT_SESSION_STORE",
        "MEMORY_BACKEND",
        "DATABASE_URL",
        "CHAT_SESSION_DATABASE_URL",
    )
    for key in keys:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    clear_settings_cache()
    return Settings(_env_file=None)


def test_create_session_store_memory_default(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _isolated_settings(
        monkeypatch,
        CHAT_SESSION_STORE="memory",
        DATABASE_URL="duckdb:///:memory:",
    )
    store = create_session_store(settings)
    assert isinstance(store, InMemorySessionStore)


def test_create_session_store_unknown_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _isolated_settings(
        monkeypatch,
        CHAT_SESSION_STORE="redis",
        DATABASE_URL="postgresql://localhost/seal",
    )
    with pytest.raises(ValueError, match="Unknown CHAT_SESSION_STORE"):
        create_session_store(settings)


def test_postgres_requires_postgres_url(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _isolated_settings(
        monkeypatch,
        CHAT_SESSION_STORE="postgres",
        DATABASE_URL="duckdb:///:memory:",
    )
    with pytest.raises(ValueError, match="Postgres URL"):
        create_session_store(settings)


def test_collect_errors_postgres_with_duckdb(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _isolated_settings(
        monkeypatch,
        CHAT_SESSION_STORE="postgres",
        DATABASE_URL="duckdb:///:memory:",
    )
    errors = collect_chat_session_store_configuration_errors(settings)
    assert len(errors) == 1
    assert "CHAT_SESSION_DATABASE_URL" in errors[0]


def test_postgres_with_duckdb_primary_and_session_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DuckDB as primary DATABASE_URL + separate Postgres for sessions."""
    from seal_core.chat.session.postgres import PostgresSessionStore

    settings = _isolated_settings(
        monkeypatch,
        CHAT_SESSION_STORE="postgres",
        DATABASE_URL="duckdb:///:memory:",
        CHAT_SESSION_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/seal",
    )
    store = create_session_store(settings)
    assert isinstance(store, PostgresSessionStore)


def test_collect_errors_duckdb_with_session_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No errors when DuckDB primary but CHAT_SESSION_DATABASE_URL is Postgres."""
    settings = _isolated_settings(
        monkeypatch,
        CHAT_SESSION_STORE="postgres",
        DATABASE_URL="duckdb:///:memory:",
        CHAT_SESSION_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/seal",
    )
    errors = collect_chat_session_store_configuration_errors(settings)
    assert errors == []


def test_memory_backend_sql_alias_normalizes_to_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _isolated_settings(
        monkeypatch,
        CHAT_SESSION_STORE="sql",
        DATABASE_URL="duckdb:///:memory:",
    )
    assert settings.chat_session_store == "postgres"
    with pytest.raises(ValueError, match="Postgres"):
        create_session_store(settings)
