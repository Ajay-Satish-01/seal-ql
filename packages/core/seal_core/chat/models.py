"""Structured models for chat orchestration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from seal_core.chat.explainability import ChatMessageExplainability  # noqa: TC001


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    explainability: ChatMessageExplainability | None = None


class ChatDecision(BaseModel):
    needs_data: bool = Field(
        ...,
        description="True if answering requires querying the database.",
    )
    confidence: Literal["high", "low"] = "high"


class ChatAnswer(BaseModel):
    message: str = Field(..., description="Natural language answer for the user.")
    suggested_queries: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Up to three example in-scope data questions.",
    )


class ChatResponsePlan(BaseModel):
    """Alias for structured final answers."""

    message: str
