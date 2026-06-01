"""Guardrails structured outputs."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class ScopeCategory(StrEnum):
    """High-level scope classification bucket."""

    DATA = "data"
    OFF_TOPIC = "off_topic"
    ABUSE = "abuse"
    AMBIGUOUS = "ambiguous"


ScopeConfidence = Literal["high", "medium", "low"]

ScopeSource = Literal["heuristic", "llm", "limits", "disabled"]

GuardrailsChannel = Literal["query", "chat"]


class ScopeDecision(BaseModel):
    """LLM scope classification result."""

    in_scope: bool = Field(
        description="True when the message is about data analysis, SQL, schema, or catalog."
    )
    reason: str = Field(
        default="",
        description="Short internal reason for the classification.",
    )
    category: ScopeCategory | None = Field(
        default=None,
        description="data | off_topic | abuse | ambiguous",
    )
    confidence: ScopeConfidence | None = Field(
        default=None,
        description="Classifier confidence: high, medium, or low.",
    )


class ScopeResult(BaseModel):
    """Combined heuristic + LLM scope check."""

    in_scope: bool
    reason: str = ""
    source: ScopeSource = Field(
        default="heuristic",
        description="How scope was determined: heuristic, llm, limits, or disabled.",
    )
    category: ScopeCategory | None = None
    confidence: ScopeConfidence | None = None


class ScopeMetadata(BaseModel):
    """Scope decision embedded in chat metadata and SSE ``seal.meta``."""

    in_scope: bool
    reason: str | None = None
    source: ScopeSource
    category: ScopeCategory | None = None
    confidence: ScopeConfidence | None = None

    @classmethod
    def from_result(cls, result: ScopeResult) -> ScopeMetadata:
        return cls(
            in_scope=result.in_scope,
            reason=result.reason,
            source=result.source,
            category=result.category,
            confidence=result.confidence,
        )
