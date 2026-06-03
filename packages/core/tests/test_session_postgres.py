"""Postgres session store tests (skip without Postgres)."""

from __future__ import annotations

import pytest
from seal_core.chat.models import ChatMessage
from seal_core.chat.session.postgres import PostgresSessionStore
from seal_core.settings import get_settings


def _store() -> PostgresSessionStore | None:
    settings = get_settings()
    if "postgres" not in settings.database_url.lower():
        return None
    url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    return PostgresSessionStore(url)


@pytest.mark.asyncio
async def test_postgres_session_roundtrip() -> None:
    store = _store()
    if store is None:
        pytest.skip("DATABASE_URL is not Postgres")

    try:
        await store.ensure_schema()
    except Exception as exc:
        pytest.skip(f"Postgres unavailable: {exc}")

    sid = await store.create_session()
    assert await store.get_session(sid) is None
    try:
        await store.append(sid, ChatMessage(role="user", content="Orders by region"))
        await store.append(sid, ChatMessage(role="assistant", content="Here is the data."))
        await store.set_database_id(sid, "default")

        page = await store.list_sessions(database_id="default")
        assert any(s.session_id == sid for s in page.sessions)

        state = await store.get_session(sid)
        assert state is not None
        assert state.title == "Orders by region"
        assert state.database_id == "default"
        assert len(state.messages) == 2

        assert await store.delete_session(sid) is True
        assert await store.get_session(sid) is None
    finally:
        await store.delete_session(sid)
        await store.close()
