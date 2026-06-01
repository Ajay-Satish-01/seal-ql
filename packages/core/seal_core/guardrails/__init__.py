"""LLM abuse guardrails — scope classification and refusal handling."""

from seal_core.guardrails.models import (
    GuardrailsChannel,
    ScopeDecision,
    ScopeMetadata,
    ScopeResult,
    ScopeSource,
)
from seal_core.guardrails.scope import (
    OUT_OF_SCOPE_QUERY_DETAIL,
    build_query_out_of_scope_detail,
    check_input_limits,
    classify_scope,
    is_in_scope,
)
from seal_core.guardrails.suggestions import merge_suggestions, suggest_queries

__all__ = [
    "GuardrailsChannel",
    "ScopeDecision",
    "ScopeMetadata",
    "ScopeResult",
    "ScopeSource",
    "OUT_OF_SCOPE_QUERY_DETAIL",
    "build_query_out_of_scope_detail",
    "classify_scope",
    "check_input_limits",
    "is_in_scope",
    "merge_suggestions",
    "suggest_queries",
]
