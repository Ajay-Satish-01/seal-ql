"""Postgres session store tests (skip without Postgres)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from seal_core.chat.explainability import ChatMessageExplainability
from seal_core.chat.models import ChatMessage
from seal_core.chat.session.postgres import (
    PostgresSessionStore,
    _explainability_to_json,
    _parse_explainability,
)
from seal_core.settings import get_settings


def test_explainability_to_json_returns_string_for_asyncpg() -> None:
    payload = _explainability_to_json(
        ChatMessage(
            role="assistant",
            content="ok",
            explainability=ChatMessageExplainability(
                sql="SELECT 1",
                sources=["orders"],
                results=[{"amount": Decimal("12.50"), "ts": datetime.now(UTC)}],
            ),
        )
    )
    assert isinstance(payload, str)
    assert '"sql": "SELECT 1"' in payload
    import json

    parsed = json.loads(payload)
    assert parsed["results"][0]["amount"] == 12.5
    assert isinstance(parsed["results"][0]["amount"], float)


def test_parse_explainability_from_dict() -> None:
    raw = {"sql": "SELECT 1", "sources": ["orders"], "metadata": {"used_sql": True}}
    result = _parse_explainability(raw)
    assert result is not None
    assert result.sql == "SELECT 1"
    assert result.sources == ["orders"]


def test_parse_explainability_from_string() -> None:
    raw = '{"sql": "SELECT 2", "sources": ["products"], "results": []}'
    result = _parse_explainability(raw)
    assert result is not None
    assert result.sql == "SELECT 2"
    assert result.sources == ["products"]


def test_parse_explainability_none_returns_none() -> None:
    assert _parse_explainability(None) is None


def test_explainability_json_roundtrip() -> None:
    original = ChatMessageExplainability(
        sql="SELECT amount FROM orders",
        sources=["orders"],
        metadata={"used_sql": True, "repair_attempts": 0},
        results=[{"amount": Decimal("99.99"), "ts": datetime(2025, 1, 1, tzinfo=UTC)}],
    )
    msg = ChatMessage(role="assistant", content="ok", explainability=original)
    json_str = _explainability_to_json(msg)
    assert json_str is not None
    restored = _parse_explainability(json_str)
    assert restored is not None
    assert restored.sql == original.sql
    assert restored.sources == original.sources
    assert restored.metadata == original.metadata
    assert restored.results[0]["amount"] == 99.99


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

    sid: str | None = None
    try:
        sid = await store.create_session()
        assert await store.get_session(sid) is None
        await store.append(sid, ChatMessage(role="user", content="Orders by region"))
        await store.append(
            sid,
            ChatMessage(
                role="assistant",
                content="Here is the data.",
                explainability=ChatMessageExplainability(
                    sql="SELECT 1",
                    sources=["orders"],
                    metadata={"used_sql": True},
                ),
            ),
        )
        await store.set_database_id(sid, "default")

        page = await store.list_sessions(database_id="default")
        assert any(s.session_id == sid for s in page.sessions)

        state = await store.get_session(sid)
        assert state is not None
        assert state.title == "Orders by region"
        assert state.database_id == "default"
        assert len(state.messages) == 2
        assert state.messages[1].explainability is not None
        assert state.messages[1].explainability.sql == "SELECT 1"

        assert await store.delete_session(sid) is True
        assert await store.get_session(sid) is None
    finally:
        if sid is not None:
            await store.delete_session(sid)
        await store.close()
