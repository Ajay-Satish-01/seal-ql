"""ChatService session persistence behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from seal_core.chat.errors import SessionDatabaseMismatchError
from seal_core.chat.service import ChatService
from seal_core.chat.session import InMemorySessionStore
from seal_core.database.registry import DatabaseBundle, DatabaseRegistry
from seal_core.guardrails.models import ScopeResult


def _service(store: InMemorySessionStore | None = None) -> ChatService:
    registry = DatabaseRegistry(
        {
            "default": DatabaseBundle(
                database_id="default",
                dialect="postgres",
                url="mock://",
                introspector=MagicMock(),
                executor=MagicMock(),
            )
        }
    )
    return ChatService(
        planner=MagicMock(),
        registry=registry,
        sessions=store or InMemorySessionStore(),
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )


@pytest.mark.asyncio
async def test_stream_incomplete_does_not_persist_messages() -> None:
    store = InMemorySessionStore()
    service = _service(store)
    ctx = await service.prepare_stream_turn(
        message="hello",
        session_id=None,
        messages_override=None,
        enhancement_enabled=False,
        database_id="default",
    )

    with (
        patch(
            "seal_core.chat.service.classify_scope",
            new=AsyncMock(return_value=ScopeResult(in_scope=True, reason="ok", source="heuristic")),
        ),
        patch.object(
            service,
            "_in_scope_turn_pipeline",
            new=AsyncMock(
                return_value=MagicMock(
                    exec_result=None,
                    chart=None,
                    meta={},
                    system="SYS",
                    reasoning=None,
                    clarification_only=False,
                )
            ),
        ),
        patch(
            "seal_core.chat.service.litellm.acompletion",
            new=AsyncMock(side_effect=RuntimeError("stream aborted")),
        ),
    ):
        chunks: list[str] = []
        async for chunk in service.stream_turn(ctx, message="hello", include_charts=False):
            chunks.append(chunk)

    payload = "".join(chunks)
    assert "event: seal.error" in payload
    assert "data: [DONE]" in payload

    state = await store.get_session(ctx.session_id)
    assert state is None or len(state.messages) == 0


@pytest.mark.asyncio
async def test_persist_turn_pins_database_after_append() -> None:
    store = InMemorySessionStore()
    service = _service(store)
    ctx = await service.prepare_stream_turn(
        message="hello",
        session_id=None,
        messages_override=None,
        enhancement_enabled=False,
        database_id="default",
    )
    await service._persist_turn_messages(
        ctx,
        user_message="hello",
        assistant_message="hi",
        pin_database=True,
    )
    state = await store.get_session(ctx.session_id)
    assert state is not None
    assert state.database_id == "default"
    assert len(state.messages) == 2


@pytest.mark.asyncio
async def test_prepare_turn_raises_on_database_mismatch() -> None:
    """Switching database_id mid-session raises SessionDatabaseMismatchError."""
    store = InMemorySessionStore()
    service = _service(store)

    ctx = await service.prepare_stream_turn(
        message="first",
        session_id=None,
        messages_override=None,
        enhancement_enabled=False,
        database_id="default",
    )
    await service._persist_turn_messages(
        ctx,
        user_message="first",
        assistant_message="answer",
        pin_database=True,
    )

    with pytest.raises(SessionDatabaseMismatchError) as exc_info:
        await service.prepare_stream_turn(
            message="second",
            session_id=ctx.session_id,
            messages_override=None,
            enhancement_enabled=False,
            database_id="analytics",
        )
    assert exc_info.value.pinned_database_id == "default"
    assert exc_info.value.requested_database_id == "analytics"
