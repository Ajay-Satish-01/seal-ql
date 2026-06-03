"""Load chat session store from settings."""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING

from seal_core.chat.session.memory import InMemorySessionStore
from seal_core.settings import Settings, get_settings

if TYPE_CHECKING:
    from seal_core.chat.session.base import BaseSessionStore

logger = logging.getLogger(__name__)

_SUPPORTED = ("memory", "postgres")


def _load_class(dotted: str) -> type:
    module_path, _, class_name = dotted.rpartition(".")
    if not module_path:
        raise ValueError(f"Invalid CHAT_SESSION_STORE_CLASS: {dotted}")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _is_postgres_url(url: str) -> bool:
    lower = url.lower()
    return "postgres" in lower and "duckdb" not in lower


def _session_database_url(settings: Settings) -> str:
    """Resolve the Postgres URL for the session store.

    Prefers ``CHAT_SESSION_DATABASE_URL`` so DuckDB-primary deployments
    can point chat history at a separate Postgres instance.
    Falls back to ``DATABASE_URL`` for single-database setups.
    """
    return settings.chat_session_database_url or settings.database_url


def _postgres_dsn(settings: Settings) -> str:
    return _session_database_url(settings).replace("postgresql+asyncpg://", "postgresql://")


def _instantiate_store_class(cls: type, settings: Settings) -> BaseSessionStore:
    """Construct a custom store, passing ``database_url`` or ``settings`` when supported."""
    dsn = _postgres_dsn(settings)
    attempts: tuple[dict[str, object], ...] = (
        {"database_url": dsn},
        {"settings": settings},
        {},
    )
    last_error: TypeError | None = None
    for kwargs in attempts:
        try:
            return cls(**kwargs)  # type: ignore[no-any-return, call-arg]
        except TypeError as exc:
            last_error = exc
    raise TypeError(
        f"{cls.__name__} must accept (), (database_url=...), or (settings=...)"
    ) from last_error


def collect_chat_session_store_configuration_errors(settings: Settings | None = None) -> list[str]:
    settings = settings or get_settings()
    backend = settings.chat_session_store.lower()
    if backend == "postgres":
        url = _session_database_url(settings)
        if not _is_postgres_url(url):
            source = (
                "CHAT_SESSION_DATABASE_URL"
                if settings.chat_session_database_url
                else "DATABASE_URL"
            )
            return [
                f"CHAT_SESSION_STORE=postgres requires a Postgres URL "
                f"(resolved {url!r} from {source}). "
                f"Set CHAT_SESSION_DATABASE_URL to a Postgres connection "
                f"string, or change CHAT_SESSION_STORE to memory."
            ]
    return []


def create_session_store(settings: Settings | None = None) -> BaseSessionStore:
    settings = settings or get_settings()

    if settings.chat_session_store_class:
        try:
            cls = _load_class(settings.chat_session_store_class)
            return _instantiate_store_class(cls, settings)
        except (ImportError, AttributeError, TypeError, ValueError) as e:
            raise RuntimeError(
                f"Failed to load CHAT_SESSION_STORE_CLASS="
                f"{settings.chat_session_store_class!r}: {e}"
            ) from e

    backend = settings.chat_session_store.lower()
    if backend in ("memory", ""):
        logger.info("Chat session store: memory (in-process)")
        return InMemorySessionStore()

    if backend in ("postgres", "sql"):
        url = _session_database_url(settings)
        if not _is_postgres_url(url):
            raise ValueError(
                "CHAT_SESSION_STORE=postgres requires a Postgres URL "
                "(set CHAT_SESSION_DATABASE_URL or use a Postgres DATABASE_URL). "
                f"Supported backends: {', '.join(_SUPPORTED)}"
            )
        from seal_core.chat.session.postgres import PostgresSessionStore

        logger.info("Chat session store: postgres (seal_app.chat_sessions)")
        return PostgresSessionStore(_postgres_dsn(settings))

    raise ValueError(
        f"Unknown CHAT_SESSION_STORE={settings.chat_session_store!r}. "
        f"Supported: {', '.join(_SUPPORTED)}"
    )
