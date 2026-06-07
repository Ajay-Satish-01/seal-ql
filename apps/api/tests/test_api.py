"""API route tests with mocked dependencies."""

from __future__ import annotations

from fastapi.testclient import TestClient
from tests.shared import AUTH_HEADERS, enable_trust_explainability


def test_health(api_client: TestClient) -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "trust_explainability_enabled": False,
    }


def test_health_reflects_trust_toggle(api_client: TestClient, monkeypatch) -> None:
    enable_trust_explainability(monkeypatch)
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "trust_explainability_enabled": True,
    }


def test_schema(api_client: TestClient) -> None:
    response = api_client.get("/v1/schema", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert "tables" in response.json()


def test_query(api_client: TestClient) -> None:
    response = api_client.post(
        "/v1/query",
        json={"query": "How many orders were placed last month?"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert "sql" in data
    assert data["sql"] == "SELECT 1 AS id LIMIT 10000"  # Sanitizer injects LIMIT
    assert len(data["results"]) == 1
    assert data["results"][0]["id"] == 1


def test_query_returns_reasoning_metadata(api_client: TestClient) -> None:
    response = api_client.post(
        "/v1/query",
        json={"query": "How many orders were placed last month?"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    reasoning = response.json()["metadata"].get("reasoning")
    assert isinstance(reasoning, dict)
    assert isinstance(reasoning.get("layers_applied"), list)


def test_query_clarification_when_ambiguous(api_client: TestClient) -> None:
    response = api_client.post(
        "/v1/query",
        json={"query": "show me trends"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sql"] == ""
    assert data["results"] == []
    assert data["columns"] == []
    assert data["metadata"]["used_sql"] is False
    reasoning = data["metadata"]["reasoning"]
    assert reasoning["clarification_required"] is True
    assert isinstance(reasoning["clarifying_questions"], list)
    assert len(reasoning["clarifying_questions"]) > 0
    assert isinstance(reasoning.get("layers_applied"), list)
    assert data["message"]


def test_query_returns_execution_metadata(api_client: TestClient) -> None:
    response = api_client.post(
        "/v1/query",
        json={"query": "How many orders were placed last month?"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    meta = response.json()["metadata"]
    assert meta["used_sql"] is True
    assert meta["database_id"] == "default"
    assert meta["row_count"] == 1
    assert isinstance(meta["execution_time_ms"], (int, float))
    assert meta["truncated"] is False
    assert isinstance(meta["warnings"], list)
    assert "repair_attempts" not in meta
