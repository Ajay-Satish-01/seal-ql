"""API route tests with mocked dependencies."""

from __future__ import annotations

from fastapi.testclient import TestClient
from tests.shared import AUTH_HEADERS


def test_health(api_client: TestClient) -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_schema(api_client: TestClient) -> None:
    response = api_client.get("/v1/schema", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert "tables" in response.json()


def test_query(api_client: TestClient) -> None:
    response = api_client.post("/v1/query", json={"query": "test query"}, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "sql" in data
    assert data["sql"] == "SELECT 1 AS id LIMIT 10000"  # Sanitizer injects LIMIT
    assert len(data["results"]) == 1
    assert data["results"][0]["id"] == 1
