"""Shared constants for API tests."""

# Non-placeholder key for pytest (must not appear in FORBIDDEN_API_KEYS).
TEST_API_KEY = "seal-pytest-api-key-0123456789abcdef0123456789abcdef"
AUTH_HEADERS = {"X-API-Key": TEST_API_KEY}
