"""Tests for default-database-only enhancement gating."""

from __future__ import annotations

from seal_core.enhancement.context import EnhancementContext
from seal_core.enhancement.default_only import default_database_only


def test_default_database_only_allows_default() -> None:
    ctx = EnhancementContext(
        session_id="s1",
        turn_id="t1",
        stage="answer",
        user_message="hello",
        base_system_prompt="BASE",
        metadata={"database_id": "default"},
    )
    assert default_database_only(ctx, feature="Test feature") is True


def test_default_database_only_blocks_non_default() -> None:
    ctx = EnhancementContext(
        session_id="s1",
        turn_id="t1",
        stage="answer",
        user_message="hello",
        base_system_prompt="BASE",
        metadata={"database_id": "analytics"},
    )
    assert default_database_only(ctx, feature="Test feature") is False
