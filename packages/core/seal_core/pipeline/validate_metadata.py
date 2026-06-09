"""Validate execution and enhancement metadata dict shapes (chat JSON + SSE)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, get_args

from seal_core.guardrails.models import ScopeSource
from seal_core.pipeline.models import (
    ENHANCEMENT_UNAVAILABLE_ORCHESTRATOR,
    VECTOR_SKIPPED_NON_DEFAULT,
    VECTOR_SKIPPED_VECTOR_STORE_DISABLED,
)
from seal_core.settings import get_settings

_SCOPE_SOURCES = frozenset(get_args(ScopeSource))
_VECTOR_SKIPPED_REASONS = frozenset(
    {VECTOR_SKIPPED_NON_DEFAULT, VECTOR_SKIPPED_VECTOR_STORE_DISABLED}
)
_UNAVAILABLE_REASONS = frozenset({ENHANCEMENT_UNAVAILABLE_ORCHESTRATOR})

logger = logging.getLogger(__name__)


class MetadataValidationError(ValueError):
    """Raised when execution metadata fails validation under strict mode."""

    def __init__(self, message: str, *, errors: list[str]) -> None:
        super().__init__(message)
        self.errors = errors


class InvalidQueryMetadataError(MetadataValidationError):
    """``QueryResponse.metadata`` failed validation."""


class InvalidStreamMetaError(MetadataValidationError):
    """SSE ``seal.meta`` payload failed validation."""


class InvalidChatMetadataError(MetadataValidationError):
    """Chat JSON ``metadata`` failed validation."""


_REPO_ROOT = Path(__file__).resolve().parents[4]
_STREAM_META_KEYS_PATH = _REPO_ROOT / "config" / "stream_meta_metadata_keys.json"
STREAM_META_METADATA_KEYS = tuple(json.loads(_STREAM_META_KEYS_PATH.read_text()))
EXECUTION_META_KEYS = frozenset(STREAM_META_METADATA_KEYS[:7])


def validate_execution_fields(meta: dict[str, Any], *, require_when_sql: bool) -> list[str]:
    """Validate execution keys on a metadata or flat stream-meta dict."""
    errors: list[str] = []
    if not require_when_sql:
        return errors
    missing = EXECUTION_META_KEYS - set(meta.keys())
    if missing:
        errors.append(f"missing execution keys when sql present: {sorted(missing)}")
    for key in ("row_count", "repair_attempts"):
        if key in meta and not isinstance(meta[key], (int, float)):
            errors.append(f"{key} must be numeric")
    if "database_id" in meta:
        database_id = meta["database_id"]
        if not isinstance(database_id, str):
            errors.append("database_id must be a string")
        elif require_when_sql and not database_id.strip():
            errors.append("database_id must be a non-empty string")
    if "warnings" in meta and not isinstance(meta["warnings"], list):
        errors.append("warnings must be an array")
    return errors


def validate_enhancement_block(
    enh: Any,
    *,
    required: bool,
) -> list[str]:
    """Validate the nested ``enhancement`` object."""
    errors: list[str] = []
    if enh is None:
        if required:
            errors.append("enhancement object required")
        return errors
    if not isinstance(enh, dict):
        errors.append("enhancement must be an object")
        return errors
    if "enabled" not in enh:
        errors.append("enhancement missing enabled")
    elif not isinstance(enh["enabled"], bool):
        errors.append("enhancement.enabled must be a boolean")
    if "applied" not in enh:
        errors.append("enhancement missing applied")
    elif not isinstance(enh["applied"], list):
        errors.append("enhancement.applied must be an array")
    elif not all(isinstance(item, str) for item in enh["applied"]):
        errors.append("enhancement.applied must be an array of strings")
    vector_skipped = enh.get("vector_skipped_reason")
    if vector_skipped is not None and (
        not isinstance(vector_skipped, str) or vector_skipped not in _VECTOR_SKIPPED_REASONS
    ):
        errors.append(
            "enhancement.vector_skipped_reason must be non_default_database or "
            "vector_store_disabled"
        )
    unavailable = enh.get("unavailable_reason")
    if unavailable is not None and (
        not isinstance(unavailable, str) or unavailable not in _UNAVAILABLE_REASONS
    ):
        errors.append("enhancement.unavailable_reason must be orchestrator_unavailable")
    return errors


def validate_explainability_fields(meta: dict[str, Any]) -> list[str]:
    """Validate optional trust/explainability metadata keys when present."""
    errors: list[str] = []
    tables_used = meta.get("tables_used")
    if tables_used is not None and (
        not isinstance(tables_used, list) or not all(isinstance(item, str) for item in tables_used)
    ):
        errors.append("tables_used must be an array of strings")
    columns_used = meta.get("columns_used")
    if columns_used is not None and (
        not isinstance(columns_used, list)
        or not all(isinstance(item, str) for item in columns_used)
    ):
        errors.append("columns_used must be an array of strings")
    catalog_matches = meta.get("catalog_matches")
    if catalog_matches is not None:
        if not isinstance(catalog_matches, list):
            errors.append("catalog_matches must be an array")
        else:
            for i, item in enumerate(catalog_matches):
                if not isinstance(item, dict) or "name" not in item:
                    errors.append(f"catalog_matches[{i}] must be an object with name")
    return errors


def validate_reasoning_block(reasoning: Any) -> list[str]:
    """Validate optional ``reasoning`` metadata object."""
    errors: list[str] = []
    if reasoning is None:
        return errors
    if not isinstance(reasoning, dict):
        errors.append("reasoning must be an object")
        return errors
    if "clarification_required" in reasoning and not isinstance(
        reasoning["clarification_required"], bool
    ):
        errors.append("reasoning.clarification_required must be a boolean")
    for key in (
        "inferred_context",
        "analysis_followups",
        "research_notes",
        "clarifying_questions",
        "layers_applied",
    ):
        value = reasoning.get(key)
        if value is None:
            continue
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            errors.append(f"reasoning.{key} must be an array of strings")
        elif len(value) > 5 and key != "layers_applied":
            errors.append(f"reasoning.{key} must have at most 5 items")
    layers_unavailable = reasoning.get("layers_unavailable")
    if layers_unavailable is not None and not isinstance(layers_unavailable, dict):
        errors.append("reasoning.layers_unavailable must be an object")
    return errors


def validate_suggested_queries(value: Any) -> list[str]:
    """Validate optional ``suggested_queries`` on refusal metadata."""
    errors: list[str] = []
    if value is None:
        return errors
    if not isinstance(value, list):
        errors.append("suggested_queries must be an array")
        return errors
    if len(value) > 3:
        errors.append("suggested_queries must have at most 3 items")
    if not all(isinstance(item, str) and item.strip() for item in value):
        errors.append("suggested_queries must be an array of non-empty strings")
    return errors


def validate_scope_block(scope: Any) -> list[str]:
    """Validate nested or flat ``scope`` metadata."""
    errors: list[str] = []
    if scope is None:
        return errors
    if not isinstance(scope, dict):
        errors.append("scope must be an object")
        return errors
    if "in_scope" not in scope or not isinstance(scope["in_scope"], bool):
        errors.append("scope.in_scope must be a boolean")
    reason = scope.get("reason")
    if reason is not None and not isinstance(reason, str):
        errors.append("scope.reason must be a string")
    source = scope.get("source")
    if source is None:
        errors.append("scope.source is required")
    elif not isinstance(source, str) or source not in _SCOPE_SOURCES:
        errors.append("scope.source must be heuristic, llm, limits, or disabled")
    return errors


def _sql_present(payload: dict[str, Any]) -> bool:
    sql_value = payload.get("sql")
    return isinstance(sql_value, str) and bool(sql_value.strip())


def _requires_enhancement_block(meta: dict[str, Any]) -> bool:
    return (
        meta.get("used_sql") is True or meta.get("refusal") is True or meta.get("sql_error") is True
    )


def _validate_boolean_flags(meta: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("used_sql", "refusal", "sql_error", "truncated", "clarification_only"):
        if key in meta and not isinstance(meta[key], bool):
            errors.append(f"{key} must be a boolean")
    return errors


def _reasoning_requires_clarification(meta: dict[str, Any]) -> bool:
    reasoning = meta.get("reasoning")
    return isinstance(reasoning, dict) and reasoning.get("clarification_required") is True


def validate_query_metadata(meta: dict[str, Any]) -> list[str]:
    """Validate ``QueryResponse.metadata`` on successful query."""
    errors: list[str] = []
    errors.extend(_validate_boolean_flags(meta))
    clarification = _reasoning_requires_clarification(meta)
    errors.extend(validate_execution_fields(meta, require_when_sql=not clarification))
    if clarification:
        if meta.get("used_sql") is not False:
            errors.append("used_sql must be false when clarification is required")
    elif meta.get("used_sql") is not True:
        errors.append("used_sql must be true on successful query")
    errors.extend(validate_explainability_fields(meta))
    if "scope" in meta:
        errors.extend(validate_scope_block(meta.get("scope")))
    errors.extend(
        validate_enhancement_block(
            meta.get("enhancement"),
            required=False,
        )
    )
    if "reasoning" in meta:
        errors.extend(validate_reasoning_block(meta.get("reasoning")))
    return errors


def enforce_query_metadata(metadata: dict[str, Any]) -> None:
    """Log or raise when query ``metadata`` fails validation."""
    errors = validate_query_metadata(metadata)
    if not errors:
        return
    logger.warning("query metadata validation errors: %s", errors)
    if get_settings().strict_stream_meta_validation:
        raise InvalidQueryMetadataError(f"invalid query metadata: {errors}", errors=errors)


def validate_nested_chat_metadata(meta: dict[str, Any], *, sql_at_top_level: bool) -> list[str]:
    """Validate ``ChatResponse.metadata`` (execution nested under ``metadata``)."""
    errors: list[str] = []
    errors.extend(_validate_boolean_flags(meta))
    errors.extend(validate_execution_fields(meta, require_when_sql=sql_at_top_level))
    errors.extend(
        validate_enhancement_block(
            meta.get("enhancement"),
            required=_requires_enhancement_block(meta),
        )
    )
    if "scope" in meta:
        errors.extend(validate_scope_block(meta.get("scope")))
    if "suggested_queries" in meta:
        errors.extend(validate_suggested_queries(meta.get("suggested_queries")))
    if "reasoning" in meta:
        errors.extend(validate_reasoning_block(meta.get("reasoning")))
    errors.extend(validate_explainability_fields(meta))
    return errors


def enforce_stream_meta_validation(meta_event: dict[str, Any]) -> None:
    """Log or raise when a ``seal.meta`` payload fails validation."""
    errors = validate_stream_meta_event(meta_event)
    if not errors:
        return
    logger.warning("seal.meta validation errors: %s", errors)
    if get_settings().strict_stream_meta_validation:
        raise InvalidStreamMetaError(f"invalid seal.meta payload: {errors}", errors=errors)


def enforce_nested_chat_metadata(
    metadata: dict[str, Any],
    *,
    sql: str | None,
) -> None:
    """Log or raise when chat JSON ``metadata`` fails validation."""
    sql_present = isinstance(sql, str) and bool(sql.strip())
    errors = validate_nested_chat_metadata(metadata, sql_at_top_level=sql_present)
    if not errors:
        return
    logger.warning("chat metadata validation errors: %s", errors)
    if get_settings().strict_stream_meta_validation:
        raise InvalidChatMetadataError(f"invalid chat metadata: {errors}", errors=errors)


def chat_response_to_stream_meta(response: dict[str, Any]) -> dict[str, Any]:
    """Flatten ``ChatResponse`` JSON into the ``seal.meta`` payload shape.

    Mirrors ``chatResponseToStreamMeta`` in ``shared/metadata-contract.ts``.
    Keep both in sync when adding fields.
    """
    meta = response.get("metadata")
    if not isinstance(meta, dict):
        meta = {}

    event: dict[str, Any] = {
        "session_id": response.get("session_id"),
        "sources": response.get("sources"),
        "sql": response.get("sql"),
        "results": response.get("results"),
        "columns": response.get("columns"),
        "chart": response.get("chart"),
    }
    for key in STREAM_META_METADATA_KEYS:
        if key in meta and meta[key] is not None:
            event[key] = meta[key]
    return event


def validate_stream_meta_event(event: dict[str, Any]) -> list[str]:
    """Validate flat JSON on the ``data:`` line of ``seal.meta`` (stream=true)."""
    errors: list[str] = []
    errors.extend(_validate_boolean_flags(event))
    session_id = event.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        errors.append("session_id must be a non-empty string")
    errors.extend(validate_execution_fields(event, require_when_sql=_sql_present(event)))
    if _requires_enhancement_block(event):
        errors.extend(
            validate_enhancement_block(
                event.get("enhancement"),
                required=True,
            )
        )
    elif event.get("enhancement") is not None:
        errors.extend(validate_enhancement_block(event.get("enhancement"), required=False))
    columns = event.get("columns")
    if columns is not None and not isinstance(columns, list):
        errors.append("columns must be an array or null")
    elif isinstance(columns, list):
        for i, col in enumerate(columns):
            if not isinstance(col, dict) or "name" not in col or "type" not in col:
                errors.append(f"columns[{i}] must have name and type")
    if event.get("scope") is not None:
        errors.extend(validate_scope_block(event.get("scope")))
    if "suggested_queries" in event:
        errors.extend(validate_suggested_queries(event.get("suggested_queries")))
    if "reasoning" in event:
        errors.extend(validate_reasoning_block(event.get("reasoning")))
    errors.extend(validate_explainability_fields(event))
    return errors
