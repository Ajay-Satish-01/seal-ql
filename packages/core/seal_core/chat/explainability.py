"""Persisted explainability snapshot on assistant chat messages."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatMessageExplainability(BaseModel):
    """SQL, metadata, and chart context for one assistant turn."""

    sql: str | None = None
    sources: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None
    chart: dict[str, Any] | None = None
    results: list[dict[str, Any]] = Field(default_factory=list)

    def has_content(self) -> bool:
        if self.sql or self.sources or self.chart or self.results:
            return True
        return bool(self.metadata)
