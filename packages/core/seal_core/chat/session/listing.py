"""Shared session list filtering and pagination helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from seal_core.chat.session.models import SessionSummary


def matches_database_filter(
    session_database_id: str | None,
    filter_database_id: str | None,
) -> bool:
    """Include unpinned sessions when filtering by database_id."""
    if filter_database_id is None:
        return True
    return session_database_id in (None, filter_database_id)


def paginate_summaries(
    summaries: list[SessionSummary],
    *,
    limit: int,
    offset: int,
) -> tuple[list[SessionSummary], bool]:
    """Sort by ``updated_at`` desc, apply offset/limit, return ``(page, has_more)``."""
    ordered = sorted(summaries, key=lambda s: s.updated_at, reverse=True)
    start = max(offset, 0)
    end = start + max(limit, 0)
    page = ordered[start:end]
    has_more = len(ordered) > end
    return page, has_more


@dataclass(frozen=True)
class SessionListPage:
    sessions: list[SessionSummary]
    has_more: bool
