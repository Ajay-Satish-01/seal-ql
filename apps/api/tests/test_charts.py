"""Tests for chart style catalog route."""

from fastapi.testclient import TestClient
from tests.factory import build_client
from tests.mocks import MockChatService
from tests.shared import AUTH_HEADERS


def test_list_chart_styles(monkeypatch) -> None:
    client: TestClient = build_client(monkeypatch)
    response = client.get("/v1/charts/styles", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert len(body["templates"]) == 4
    assert len(body["color_schemes"]) == 6
    assert body["templates"][0]["id"] == "default"
    assert "swatches" in body["color_schemes"][0]


def test_query_without_chart_style_omits_style_metadata(monkeypatch) -> None:
    client: TestClient = build_client(monkeypatch)
    response = client.post(
        "/v1/query",
        json={"query": "How many orders?"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    chart = response.json().get("chart") or {}
    metadata = chart.get("metadata") or {}
    assert "template" not in metadata
    assert "color_scheme" not in metadata


def test_query_with_chart_style_records_metadata(monkeypatch) -> None:
    client: TestClient = build_client(monkeypatch)
    response = client.post(
        "/v1/query",
        json={
            "query": "How many orders?",
            "chart_style": {"template": "rounded", "color_scheme": "tableau10"},
        },
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    metadata = (response.json().get("chart") or {}).get("metadata") or {}
    assert metadata.get("template") == "rounded"
    assert metadata.get("color_scheme") == "tableau10"


def test_query_invalid_chart_style_returns_422(monkeypatch) -> None:
    client: TestClient = build_client(monkeypatch)
    response = client.post(
        "/v1/query",
        json={
            "query": "How many orders?",
            "chart_style": {"template": "neon", "color_scheme": "tableau10"},
        },
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 422


def test_chat_forwards_chart_style(monkeypatch) -> None:
    MockChatService.last_chart_style = None
    client: TestClient = build_client(monkeypatch)
    response = client.post(
        "/v1/chat",
        json={
            "message": "Hi",
            "include_charts": True,
            "chart_style": {"template": "minimal", "color_scheme": "viridis"},
        },
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    assert MockChatService.last_chart_style is not None
    assert MockChatService.last_chart_style.template.value == "minimal"
    assert MockChatService.last_chart_style.color_scheme.value == "viridis"
