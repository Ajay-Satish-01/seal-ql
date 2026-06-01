"""Validate execution and enhancement metadata dict shapes (chat JSON + SSE)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from seal_core.settings import get_settings

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
    if "database_id" in meta and not isinstance(meta["database_id"], str):
        errors.append("database_id must be a string")
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
    for key in ("used_sql", "refusal", "sql_error", "truncated"):
        if key in meta and not isinstance(meta[key], bool):
            errors.append(f"{key} must be a boolean")
    return errors


def validate_query_metadata(meta: dict[str, Any]) -> list[str]:
    """Validate ``QueryResponse.metadata`` on successful query."""
    errors: list[str] = []
    errors.extend(_validate_boolean_flags(meta))
    errors.extend(validate_execution_fields(meta, require_when_sql=True))
    if meta.get("used_sql") is not True:
        errors.append("used_sql must be true on successful query")
    errors.extend(
        validate_enhancement_block(
            meta.get("enhancement"),
            required=False,
        )
    )
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
    errors.extend(
        validate_enhancement_block(
            event.get("enhancement"),
            required=_requires_enhancement_block(event),
        )
    )
    columns = event.get("columns")
    if columns is not None and not isinstance(columns, list):
        errors.append("columns must be an array or null")
    elif isinstance(columns, list):
        for i, col in enumerate(columns):
            if not isinstance(col, dict) or "name" not in col or "type" not in col:
                errors.append(f"columns[{i}] must have name and type")
    return errors
