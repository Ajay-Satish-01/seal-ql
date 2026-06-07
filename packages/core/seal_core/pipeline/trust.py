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


def _is_schema_sensitive_note(note: str) -> bool:
    lower = note.lower()
    if note.startswith("Data sourced from:"):
        return True
    if "schema exposes " in lower:
        return True
    if " table" in lower or "table " in lower:
        return True
    return bool(" column" in lower or "column " in lower)


def strip_trust_reasoning(reasoning: dict[str, Any]) -> dict[str, Any]:
    """Remove table-name leakage from reasoning research notes when trust is off."""
    notes = reasoning.get("research_notes")
    if not isinstance(notes, list):
        return reasoning
    filtered = [
        note for note in notes if isinstance(note, str) and not _is_schema_sensitive_note(note)
    ]
    if filtered == notes:
        return reasoning
    gated = dict(reasoning)
    gated["research_notes"] = filtered
    return gated


def strip_trust_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Remove trust-only metadata keys."""
    gated = {key: value for key, value in metadata.items() if key not in TRUST_METADATA_KEYS}
    reasoning = gated.get("reasoning")
    if isinstance(reasoning, dict):
        gated["reasoning"] = strip_trust_reasoning(reasoning)
    return gated


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
    reasoning = gated.get("reasoning")
    if isinstance(reasoning, dict):
        gated["reasoning"] = strip_trust_reasoning(reasoning)
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


def apply_trust_gating_to_stored_explainability(
    explainability: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Strip trust fields from persisted session explainability on read.

    Returns ``None`` when gating leaves no meaningful content so the API
    omits the field entirely instead of returning an empty shell.
    """
    if explainability is None or is_trust_explainability_enabled():
        return explainability
    gated = dict(explainability)
    gated["sql"] = None
    gated["sources"] = []
    gated["results"] = []
    gated["chart"] = None
    metadata = gated.get("metadata")
    if isinstance(metadata, dict):
        gated["metadata"] = strip_trust_metadata(metadata)
    remaining_meta = gated.get("metadata")
    if not isinstance(remaining_meta, dict) or not remaining_meta:
        return None
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
