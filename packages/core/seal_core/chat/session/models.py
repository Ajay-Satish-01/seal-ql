"""Session state models for chat history."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from seal_core.chat.models import ChatMessage


@dataclass
class SessionState:
    messages: list[ChatMessage] = field(default_factory=list)
    #: Parallel to ``messages`` (epoch seconds); ``None`` for in-memory store entries.
    message_timestamps: list[float | None] = field(default_factory=list)
    summary: str | None = None
    summary_through_index: int = 0
    database_id: str | None = None
    title: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class SessionSummary:
    """Lightweight model for session list endpoints."""

    session_id: str
    title: str | None
    database_id: str | None
    message_count: int
    created_at: float
    updated_at: float
