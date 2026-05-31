"""Merge workspace patches with env defaults and hot-reload."""

from __future__ import annotations

from typing import Any

from seal_core.settings import apply_runtime_overrides, get_settings
from seal_core.workspace.settings_schema import schema_by_key


def _serialize_value(key: str, value: Any) -> Any:
    """Normalize Settings attributes for workspace API (JSON-friendly)."""
    if key == "cors_origins" and isinstance(value, list):
        return ",".join(value)
    return value


def _deserialize_patch_value(key: str, value: Any) -> Any:
    if key == "cors_origins" and isinstance(value, str):
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    return value


def current_values() -> dict[str, Any]:
    """Workspace-managed keys from environment / ``.env`` (base layer)."""
    settings = get_settings()
    return {key: _serialize_value(key, getattr(settings, key)) for key in schema_by_key()}


def effective_settings_from_stored(stored: dict[str, Any]) -> dict[str, Any]:
    """Merge persisted workspace overrides onto env defaults (unmasked)."""
    base = current_values()
    if stored:
        base.update(stored)
    return base


def effective_settings_for_api(stored: dict[str, Any]) -> dict[str, Any]:
    """API-facing effective settings (env ← stored, masked secrets)."""
    return workspace_api_values(effective_settings_from_stored(stored))


def merge_workspace_patch(patch: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    """Validate patch; return (merged_values, hot_reload_keys, restart_required_keys)."""
    fields = schema_by_key()
    unknown = [k for k in patch if k not in fields]
    if unknown:
        raise ValueError(f"Unknown settings: {', '.join(unknown)}")

    base = current_values()
    hot: list[str] = []
    restart: list[str] = []
    for key, value in patch.items():
        field = fields[key]
        if field.value_type == "bool" and not isinstance(value, bool):
            raise ValueError(f"{key} must be a boolean")
        if field.value_type == "int" and (not isinstance(value, int) or value < 1):
            raise ValueError(f"{key} must be a positive integer")
        if field.value_type == "str" and not isinstance(value, str):
            raise ValueError(f"{key} must be a string")
        base[key] = _deserialize_patch_value(key, value)
        (hot if field.hot_reload else restart).append(key)
    return base, hot, restart


_MASKED = "***"


def mask_secret_values(values: dict[str, Any]) -> dict[str, Any]:
    """Redact secret workspace fields for API responses."""
    fields = schema_by_key()
    out: dict[str, Any] = {}
    for key, value in values.items():
        field = fields.get(key)
        if field is not None and field.secret and value:
            out[key] = _MASKED
        else:
            out[key] = _serialize_value(key, value)
    return out


def workspace_api_values(values: dict[str, Any]) -> dict[str, Any]:
    """Return settings dict suitable for workspace GET/PATCH JSON responses."""
    masked = mask_secret_values({key: values[key] for key in schema_by_key() if key in values})
    return masked


def apply_hot_reload(values: dict[str, Any], keys: list[str]) -> None:
    """Apply hot-reload keys to the in-process Settings singleton."""
    if not keys:
        return
    updates = {k: _deserialize_patch_value(k, values[k]) for k in keys}
    apply_runtime_overrides(updates)


def build_patch_result(
    merged: dict[str, Any],
    hot_keys: list[str],
    restart_keys: list[str],
    *,
    apply_hot_reload_now: bool,
) -> dict[str, Any]:
    """Build workspace PATCH/apply API payload."""
    applied: list[str] = []
    pending: list[str] = []
    if hot_keys:
        if apply_hot_reload_now:
            apply_hot_reload(merged, hot_keys)
            applied = list(hot_keys)
        else:
            pending = list(hot_keys)
    return {
        "settings": workspace_api_values(merged),
        "hot_reload_applied": applied,
        "pending_apply": pending,
        "restart_required": restart_keys,
    }


def apply_persisted_hot_reload(merged: dict[str, Any], hot_keys: list[str]) -> dict[str, Any]:
    """Apply stored hot-reload keys to the running process (prod dashboard button)."""
    if hot_keys:
        apply_hot_reload(merged, hot_keys)
    return {
        "settings": workspace_api_values(merged),
        "hot_reload_applied": list(hot_keys),
        "pending_apply": [],
    }


def classify_keys(keys: list[str]) -> tuple[list[str], list[str]]:
    """Split keys into ``(hot_reload_keys, restart_required_keys)`` via schema metadata."""
    fields = schema_by_key()
    hot = [k for k in keys if k in fields and fields[k].hot_reload]
    restart = [k for k in keys if k in fields and not fields[k].hot_reload]
    return hot, restart


def _is_masked_secret(key: str, value: Any) -> bool:
    """A masked sentinel echoed back from a GET must never be persisted."""
    field = schema_by_key().get(key)
    return bool(field is not None and field.secret and value == _MASKED)


def overrides_only(stored: dict[str, Any]) -> dict[str, Any]:
    """Keep only persisted keys that differ from the ``.env``/base defaults.

    This keeps ``.env`` as the real fallback: values equal to the base layer are
    not snapshotted, so later environment changes still take effect.
    """
    base = current_values()
    fields = schema_by_key()
    return {key: value for key, value in stored.items() if key in fields and value != base.get(key)}


def prepare_settings_patch(
    stored: dict[str, Any], patch: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], list[str], list[str]]:
    """Validate and normalize a settings patch.

    Returns ``(overrides_to_persist, effective_merged, hot_keys, restart_keys)``:

    - Masked secret placeholders are dropped (never persisted).
    - Only keys differing from the ``.env`` base are persisted.
    - hot/restart keys reflect only values that actually changed.
    """
    cleaned = {k: v for k, v in patch.items() if not _is_masked_secret(k, v)}
    merge_workspace_patch(cleaned)  # validate types / reject unknown keys

    # Classify the submitted keys (the dashboard sends only fields the user
    # edited), so hot/restart reporting reflects what was actually requested.
    hot_keys, restart_keys = classify_keys(list(cleaned))

    base = current_values()
    persisted = overrides_only({**stored, **cleaned})
    merged = {**base, **persisted}
    return persisted, merged, hot_keys, restart_keys


def prepare_apply_persisted(
    stored: dict[str, Any],
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Effective settings + hot/restart keys derived from persisted overrides only."""
    merged = effective_settings_from_stored(stored)
    fields = schema_by_key()
    hot_keys, restart_keys = classify_keys([k for k in stored if k in fields])
    return merged, hot_keys, restart_keys
