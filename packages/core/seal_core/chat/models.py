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
    clarification_required: bool = Field(
        default=False,
        description="True when the user message lacks enough detail for a confident answer.",
    )
    clarifying_questions: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Targeted questions to gather missing requirements.",
    )
    inferred_context: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Concise inferences from prior session turns.",
    )


class ChatAnswerReasoningFields(BaseModel):
    """Shared structured reasoning fields for final chat answers."""

    analysis_followups: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Suggested analytical follow-up questions or angles.",
    )
    research_notes: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Concise data-backed observations tied to returned results.",
    )


class ChatAnswer(ChatAnswerReasoningFields):
    message: str = Field(..., description="Natural language answer for the user.")
    suggested_queries: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Up to three example in-scope data questions.",
    )


class ChatAnswerEnrichment(ChatAnswerReasoningFields):
    """Structured follow-ups for streamed answers (message already produced)."""


class ChatResponsePlan(BaseModel):
    """Alias for structured final answers."""

    message: str
