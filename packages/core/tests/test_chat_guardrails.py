"""Chat service guardrails integration (refusal path skips SQL)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from seal_core.chat.errors import SessionDatabaseMismatchError
from seal_core.chat.service import ChatService
from seal_core.chat.sessions import SessionStore
from seal_core.guardrails.models import ScopeResult


@pytest.mark.asyncio
async def test_run_turn_out_of_scope_skips_execute_path() -> None:
    from seal_core.database.registry import DatabaseBundle, DatabaseRegistry

    planner = MagicMock()
    executor = MagicMock()
    introspector = MagicMock()
    introspector.introspect = AsyncMock()
    registry = DatabaseRegistry(
        {
            "default": DatabaseBundle(
                database_id="default",
                dialect="postgres",
                url="mock://",
                introspector=introspector,
                executor=executor,
            )
        }
    )
    service = ChatService(
        planner=planner,
        registry=registry,
        sessions=SessionStore(),
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )
    refusal = MagicMock()
    refusal.message = "I only answer data questions."
    refusal.session_id = "s1"
    refusal.sources = []
    refusal.sql = None
    refusal.results = None
    refusal.columns = None
    refusal.chart = None
    refusal.metadata = {"refusal": True}

    with (
        patch(
            "seal_core.chat.service.classify_scope",
            new=AsyncMock(
                return_value=ScopeResult(
                    in_scope=False,
                    reason="off-topic",
                    source="heuristic",
                )
            ),
        ),
        patch.object(service, "_refusal_turn", new=AsyncMock(return_value=refusal)),
        patch.object(service, "_execute_data_path", new=AsyncMock()) as execute_mock,
    ):
        ctx = service._prepare_turn(
            "write me a poem",
            None,
            None,
            None,
            "default",
        )
        result = await service._run_turn(ctx, include_charts=True)

    execute_mock.assert_not_called()
    introspector.introspect.assert_not_called()
    assert result.sql is None
    assert result.metadata.get("refusal") is True


def test_prepare_turn_rejects_mismatched_database_id() -> None:
    from seal_core.database.registry import DatabaseBundle, DatabaseRegistry

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
    service = ChatService(
        planner=MagicMock(),
        registry=registry,
        sessions=SessionStore(),
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )
    ctx1 = service._prepare_turn("hello", None, None, None, "default")
    service._complete_turn(ctx1)
    with pytest.raises(SessionDatabaseMismatchError, match="pinned"):
        service._prepare_turn("follow up", ctx1.session_id, None, None, "analytics")


def test_session_not_pinned_until_explicit_pin() -> None:
    from seal_core.database.registry import DatabaseBundle, DatabaseRegistry

    registry = DatabaseRegistry(
        {
            "default": DatabaseBundle(
                database_id="default",
                dialect="postgres",
                url="mock://",
                introspector=MagicMock(),
                executor=MagicMock(),
            ),
            "analytics": DatabaseBundle(
                database_id="analytics",
                dialect="duckdb",
                url=":memory:",
                introspector=MagicMock(),
                executor=MagicMock(),
            ),
        }
    )
    sessions = SessionStore()
    service = ChatService(
        planner=MagicMock(),
        registry=registry,
        sessions=sessions,
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )
    ctx = service._prepare_turn("hello", None, None, None, "analytics")
    _, state = sessions.get_or_create(ctx.session_id)
    assert state.database_id is None
    service._prepare_turn("retry", ctx.session_id, None, None, "default")


@pytest.mark.asyncio
async def test_refusal_metadata_includes_database_id_and_does_not_pin() -> None:
    from seal_core.database.registry import DatabaseBundle, DatabaseRegistry

    registry = DatabaseRegistry(
        {
            "default": DatabaseBundle(
                database_id="default",
                dialect="postgres",
                url="mock://",
                introspector=MagicMock(),
                executor=MagicMock(),
            ),
            "analytics": DatabaseBundle(
                database_id="analytics",
                dialect="duckdb",
                url=":memory:",
                introspector=MagicMock(),
                executor=MagicMock(),
            ),
        }
    )
    sessions = SessionStore()
    service = ChatService(
        planner=MagicMock(),
        registry=registry,
        sessions=sessions,
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )

    with patch(
        "seal_core.chat.service.classify_scope",
        new=AsyncMock(
            return_value=ScopeResult(
                in_scope=False,
                reason="too long",
                source="limits",
            )
        ),
    ):
        result = await service.handle_json(
            message="write me a poem",
            session_id=None,
            messages_override=None,
            include_charts=False,
            enhancement_enabled=None,
            database_id="analytics",
        )

    _, state = sessions.get_or_create(result.session_id)
    assert state.database_id is None
    assert result.metadata["database_id"] == "analytics"
    assert result.metadata["refusal"] is True
    assert result.metadata["used_sql"] is False


def test_handle_stream_rejects_mismatched_database_id_synchronously() -> None:
    from seal_core.database.registry import DatabaseBundle, DatabaseRegistry

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
    service = ChatService(
        planner=MagicMock(),
        registry=registry,
        sessions=SessionStore(),
        orchestrator=None,
        catalog=None,
        semantic_registry=None,
    )
    ctx = service._prepare_turn("hello", None, None, None, "default")
    service._complete_turn(ctx)

    with pytest.raises(SessionDatabaseMismatchError):
        service.handle_stream(
            message="follow up",
            session_id=ctx.session_id,
            messages_override=None,
            include_charts=False,
            enhancement_enabled=None,
            database_id="analytics",
        )
