"""Shared constants for API tests."""

from __future__ import annotations

import os

# Non-placeholder key for in-process TestClient tests (conftest autouse).
TEST_API_KEY = "seal-pytest-api-key-0123456789abcdef0123456789abcdef"
AUTH_HEADERS = {"X-API-Key": TEST_API_KEY}

# Compose / CI default (.env.example). Running API container uses this, not TEST_API_KEY.
LIVE_API_KEY = "seal-ci-test-api-key-0123456789abcdef0123456789abcdef"


def live_api_headers() -> dict[str, str]:
    """X-API-Key for httpx tests against a live docker compose API.

    Do not read ``SEAL_API_KEY`` here — conftest autouse overwrites it with
    ``TEST_API_KEY`` for in-process tests, which mismatches the running stack.
    Set ``SEAL_LIVE_API_KEY`` only when your ``.env`` uses a custom secret
    (empty or unset values fall back to ``LIVE_API_KEY``).
    """
    return {"X-API-Key": os.environ.get("SEAL_LIVE_API_KEY") or LIVE_API_KEY}
