"""Shared authentication constants for Seal API deployments."""

from __future__ import annotations

# Known weak or documented placeholder keys — rejected at API startup.
FORBIDDEN_API_KEYS: frozenset[str] = frozenset(
    {
        "dev-local-change-me",
        "replace-me-with-openssl-rand-hex-32",
        "changeme",
        "change-me",
        "your-secret",
        "your-secret-here",
    }
)


def is_forbidden_api_key(key: str) -> bool:
    """Return True if ``key`` is an obvious placeholder (case-insensitive)."""
    normalized = key.strip().lower()
    if not normalized:
        return False
    if normalized in FORBIDDEN_API_KEYS:
        return True
    return normalized.startswith("replace-me")
