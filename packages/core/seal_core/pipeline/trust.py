"""Trust / explainability visibility gating for API and SSE payloads."""

from __future__ import annotations

from typing import Any

from seal_core.settings import get_settings

# Metadata keys omitted when trust explainability is disabled.
TRUST_METADATA_KEYS = frozenset(
    {
        "tables_used",
        "columns_used",
        "catalog_matches",
        "repair_attempts",
        "scope",
    }
)

# Chat / SSE top-level fields omitted when trust explainability is disabled.
TRUST_TOP_LEVEL_KEYS = frozenset(
    {
        "sources",
        "sql",
        "results",
        "columns",
    }
)


def is_trust_explainability_enabled() -> bool:
    """Return whether trust/explainability fields are exposed to clients."""
    return get_settings().trust_explainability_enabled


def strip_trust_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Remove trust-only metadata keys."""
    return {key: value for key, value in metadata.items() if key not in TRUST_METADATA_KEYS}


def apply_trust_gating_to_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Strip trust metadata when ``SEAL_TRUST_EXPLAINABILITY_ENABLED`` is false."""
    if is_trust_explainability_enabled():
        return metadata
    return strip_trust_metadata(metadata)


def apply_trust_gating_to_stream_meta(event: dict[str, Any]) -> dict[str, Any]:
    """Strip trust fields from flat ``seal.meta`` payloads."""
    if is_trust_explainability_enabled():
        return event
    gated = {key: value for key, value in event.items() if key not in TRUST_TOP_LEVEL_KEYS}
    gated = strip_trust_metadata(gated)
    return gated


def apply_trust_gating_to_chat_response(response: dict[str, Any]) -> dict[str, Any]:
    """Strip trust fields from chat JSON responses."""
    if is_trust_explainability_enabled():
        return response
    gated = dict(response)
    for key in TRUST_TOP_LEVEL_KEYS:
        if key in gated:
            if key == "sources":
                gated[key] = []
            else:
                gated[key] = None
    metadata = gated.get("metadata")
    if isinstance(metadata, dict):
        gated["metadata"] = strip_trust_metadata(metadata)
    return gated


def apply_trust_gating_to_query_response(response: dict[str, Any]) -> dict[str, Any]:
    """Strip trust fields from query JSON responses (sql/results remain)."""
    if is_trust_explainability_enabled():
        return response
    gated = dict(response)
    if "sources" in gated:
        gated["sources"] = []
    metadata = gated.get("metadata")
    if isinstance(metadata, dict):
        gated["metadata"] = strip_trust_metadata(metadata)
    return gated
