"""In-memory session store tests."""

from __future__ import annotations

import time

import pytest
from seal_core.chat.explainability import ChatMessageExplainability
from seal_core.chat.models import ChatMessage
from seal_core.chat.session import InMemorySessionStore
from seal_core.settings import clear_settings_cache


@pytest.mark.asyncio
async def test_append_persists_assistant_explainability() -> None:
    store = InMemorySessionStore()
    sid = await store.create_session()
    explainability = ChatMessageExplainability(
        sql="SELECT 1",
        sources=["orders"],
        metadata={"used_sql": True, "row_count": 1},
        results=[{"n": 1}],
    )
    await store.append(sid, ChatMessage(role="user", content="Count orders"))
    await store.append(
        sid,
        ChatMessage(role="assistant", content="One row.", explainability=explainability),
    )

    state = await store.get_session(sid)
    assert state is not None
    assistant = state.messages[1]
    assert assistant.explainability is not None
    assert assistant.explainability.sql == "SELECT 1"
    assert assistant.explainability.sources == ["orders"]


@pytest.mark.asyncio
async def test_create_append_list_get_delete() -> None:
    store = InMemorySessionStore()
    sid = await store.create_session()
    await store.append(sid, ChatMessage(role="user", content="Hello world"))
    await store.append(sid, ChatMessage(role="assistant", content="Hi there"))

    page = await store.list_sessions()
    assert len(page.sessions) == 1
    assert page.sessions[0].session_id == sid
    assert page.sessions[0].title == "Hello world"
    assert page.sessions[0].message_count == 2

    state = await store.get_session(sid)
    assert state is not None
    assert len(state.messages) == 2

    assert await store.delete_session(sid) is True
    assert await store.get_session(sid) is None


@pytest.mark.asyncio
async def test_list_sessions_includes_unpinned_when_filtering_database() -> None:
    store = InMemorySessionStore()
    sid = await store.create_session()
    await store.append(sid, ChatMessage(role="user", content="Unpinned chat"))

    filtered = await store.list_sessions(database_id="analytics")
    assert any(s.session_id == sid for s in filtered.sessions)

    pinned_other = await store.create_session()
    await store.append(pinned_other, ChatMessage(role="user", content="Other db"))
    await store.set_database_id(pinned_other, "default")

    analytics_only = await store.list_sessions(database_id="analytics")
    assert any(s.session_id == sid for s in analytics_only.sessions)
    assert not any(s.session_id == pinned_other for s in analytics_only.sessions)


@pytest.mark.asyncio
async def test_create_session_not_listed_until_append() -> None:
    store = InMemorySessionStore()
    sid = await store.create_session()
    page = await store.list_sessions()
    assert page.sessions == []
    await store.append(sid, ChatMessage(role="user", content="Hi"))
    page = await store.list_sessions()
    assert any(s.session_id == sid for s in page.sessions)


@pytest.mark.asyncio
async def test_list_sessions_pagination() -> None:
    store = InMemorySessionStore()
    sids: list[str] = []
    for i in range(5):
        sid = await store.create_session()
        await store.append(sid, ChatMessage(role="user", content=f"Chat {i}"))
        sids.append(sid)

    page1 = await store.list_sessions(limit=2, offset=0)
    assert len(page1.sessions) == 2
    assert page1.has_more is True

    page2 = await store.list_sessions(limit=2, offset=2)
    assert len(page2.sessions) == 2
    assert page2.has_more is True

    page3 = await store.list_sessions(limit=2, offset=4)
    assert len(page3.sessions) == 1
    assert page3.has_more is False

    all_ids = {s.session_id for p in [page1, page2, page3] for s in p.sessions}
    assert all_ids == set(sids)


@pytest.mark.asyncio
async def test_list_sessions_default_limit_clamps() -> None:
    store = InMemorySessionStore()
    for i in range(3):
        sid = await store.create_session()
        await store.append(sid, ChatMessage(role="user", content=f"Chat {i}"))

    page = await store.list_sessions(limit=9999)
    assert len(page.sessions) == 3
    assert page.has_more is False


@pytest.mark.asyncio
async def test_set_database_id_pins_session() -> None:
    store = InMemorySessionStore()
    sid = await store.create_session()
    await store.append(sid, ChatMessage(role="user", content="hi"))
    await store.set_database_id(sid, "analytics")
    state = await store.get_session(sid)
    assert state is not None
    assert state.database_id == "analytics"


@pytest.mark.asyncio
async def test_set_database_id_pin_once_ignores_second_call() -> None:
    """Once pinned, a second set_database_id with a different id is a no-op."""
    store = InMemorySessionStore()
    sid = await store.create_session()
    await store.append(sid, ChatMessage(role="user", content="hi"))
    await store.set_database_id(sid, "analytics")
    await store.set_database_id(sid, "default")
    state = await store.get_session(sid)
    assert state is not None
    assert state.database_id == "analytics"


@pytest.mark.asyncio
async def test_set_database_id_on_missing_session_is_noop() -> None:
    """set_database_id on a deleted/expired session must not create phantom state."""
    store = InMemorySessionStore()
    sid = await store.create_session()
    await store.set_database_id(sid, "analytics")
    state = await store.get_session(sid)
    assert state is None


@pytest.mark.asyncio
async def test_delete_session_returns_false_for_missing() -> None:
    store = InMemorySessionStore()
    sid = await store.create_session()
    assert await store.delete_session(sid) is False


@pytest.mark.asyncio
async def test_ttl_expires_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv("CHAT_SESSION_TTL_SECONDS", "1")
    clear_settings_cache()

    store = InMemorySessionStore()
    sid = await store.create_session()
    await store.append(sid, ChatMessage(role="user", content="old"))
    time.sleep(1.1)
    assert await store.get_session(sid) is None
    # set_database_id on expired session must not resurrect it
    await store.set_database_id(sid, "analytics")
    assert await store.get_session(sid) is None
    clear_settings_cache()
