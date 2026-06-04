"""API tests for LLM failure HTTP mapping."""

from __future__ import annotations

from unittest.mock import patch

import litellm
from fastapi.testclient import TestClient
from seal_core.guardrails.models import ScopeResult
from tests.shared import AUTH_HEADERS


def test_query_maps_unknown_model_to_502(api_client: TestClient) -> None:
    exc = litellm.NotFoundError(
        message="model missing",
        llm_provider="gemini",
        model="gemini/bad",
    )

    async def boom(*_args: object, **_kwargs: object) -> None:
        raise exc

    async def in_scope(*_args: object, **_kwargs: object) -> ScopeResult:
        return ScopeResult(in_scope=True, reason="ok", suggested_queries=[])

    with (
        patch("app.routes.query.classify_scope", new=in_scope),
        patch("app.routes.query.execute_natural_language_query", new=boom),
    ):
        response = api_client.post(
            "/v1/query",
            json={"query": "How many users?"},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 502
    assert "LLM_MODEL" in response.json()["detail"]
