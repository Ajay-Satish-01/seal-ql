"""LLM abuse guardrails — scope classification and refusal handling."""

from seal_core.guardrails.models import ScopeDecision, ScopeResult
from seal_core.guardrails.scope import (
    OUT_OF_SCOPE_QUERY_DETAIL,
    check_input_limits,
    classify_scope,
    is_in_scope,
)

__all__ = [
    "ScopeDecision",
    "ScopeResult",
    "OUT_OF_SCOPE_QUERY_DETAIL",
    "classify_scope",
    "check_input_limits",
    "is_in_scope",
]
