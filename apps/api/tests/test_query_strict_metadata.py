"""API tests for strict query metadata validation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from seal_core.settings import _load_settings
from tests.shared import AUTH_HEADERS


def test_query_strict_metadata_validation_returns_500(api_client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("STRICT_STREAM_META_VALIDATION", "true")
    _load_settings.cache_clear()
    try:
        bad = MagicMock()
        bad.model_dump.return_value = {
            "database_id": "default",
            "used_sql": True,
        }
        with patch("app.routes.query.ExecutionMetadata.from_execute_result", return_value=bad):
            response = api_client.post(
                "/v1/query",
                json={"query": "How many orders were placed last month?"},
                headers=AUTH_HEADERS,
            )
        assert response.status_code == 500
    finally:
        _load_settings.cache_clear()
