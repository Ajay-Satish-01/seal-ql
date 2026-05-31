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
    source: str = Field(
        default="heuristic",
        description="heuristic | llm | limits | disabled",
    )
    category: ScopeCategory | None = None
    confidence: ScopeConfidence | None = None
