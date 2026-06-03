"""Session id parsing tests."""

from __future__ import annotations

import pytest
from seal_core.chat.session.ids import InvalidSessionIdError, parse_session_id


def test_parse_session_id_accepts_canonical_uuid() -> None:
    raw = "550e8400-e29b-41d4-a716-446655440000"
    assert parse_session_id(raw) == raw


def test_parse_session_id_rejects_invalid() -> None:
    with pytest.raises(InvalidSessionIdError):
        parse_session_id("not-a-uuid")
