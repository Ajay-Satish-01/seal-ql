"""Scope gate: limits, heuristics, and LLM classification."""

from __future__ import annotations

import logging

from seal_core.guardrails.heuristics import heuristic_in_scope
from seal_core.guardrails.models import (
    GuardrailsChannel,
    ScopeCategory,
    ScopeDecision,
    ScopeResult,
)
from seal_core.guardrails.prompts import SCOPE_CLASSIFY_SYSTEM
from seal_core.llm.client import get_api_base, get_api_key, get_async_client, get_model
from seal_core.settings import get_settings

logger = logging.getLogger(__name__)

OUT_OF_SCOPE_QUERY_DETAIL = "query_out_of_scope"


def check_input_limits(
    text: str,
    *,
    max_chars: int,
    label: str,
) -> ScopeResult | None:
    if len(text) > max_chars:
        return ScopeResult(
            in_scope=False,
            reason=f"{label} exceeds {max_chars} characters",
            source="limits",
            category=ScopeCategory.ABUSE,
            confidence="high",
        )
    return None


async def classify_scope(text: str, *, channel: GuardrailsChannel) -> ScopeResult:
    """Classify message scope for the query or chat API channel."""
    settings = get_settings()

    # Input-size limits are a denial-of-service / cost control that is independent
    # of scope classification, so enforce them even when guardrails are disabled.
    # Otherwise disabling guardrails would silently remove the configured cap and
    # let oversized payloads reach the LLM.
    limit = settings.max_query_chars if channel == "query" else settings.max_chat_message_chars
    over = check_input_limits(text, max_chars=limit, label=channel)
    if over is not None:
        return over

    if not settings.guardrails_enabled:
        return ScopeResult(in_scope=True, reason="guardrails disabled", source="disabled")

    hint = heuristic_in_scope(text)
    if hint is True:
        return ScopeResult(
            in_scope=True,
            reason="data keywords",
            source="heuristic",
            category=ScopeCategory.DATA,
            confidence="high",
        )
    if hint is False:
        return ScopeResult(
            in_scope=False,
            reason="off-topic pattern",
            source="heuristic",
            category=ScopeCategory.ABUSE,
            confidence="high",
        )

    client = get_async_client()
    model = get_model()
    try:
        decision: ScopeDecision = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SCOPE_CLASSIFY_SYSTEM},
                {"role": "user", "content": text},
            ],
            response_model=ScopeDecision,
            api_base=get_api_base(),
            api_key=get_api_key(),
            max_retries=settings.llm_max_retries,
        )
        return ScopeResult(
            in_scope=decision.in_scope,
            reason=decision.reason,
            source="llm",
            category=decision.category,
            confidence=decision.confidence,
        )
    except Exception as exc:
        logger.warning("Scope classification failed: %s", exc)
        fail_closed = settings.guardrails_fail_closed
        return ScopeResult(
            in_scope=not fail_closed,
            reason="classification error",
            source="llm",
        )


async def is_in_scope(text: str, *, channel: GuardrailsChannel) -> ScopeResult:
    return await classify_scope(text, channel=channel)
