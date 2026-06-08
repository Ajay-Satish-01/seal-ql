"""Live end-to-end tests against the Docker stack (no dependency mocks)."""

from __future__ import annotations

import httpx
import pytest
from tests.e2e_llm_helpers import (
    assert_chat_json_body,
    assert_query_json_body,
    post_chat_json,
    skip_if_llm_unavailable,
)
from tests.shared import live_api_headers

pytest_plugins = ["tests.live_http_fixtures"]


def test_e2e_health(live_http: httpx.Client) -> None:
    r = live_http.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_e2e_get_catalog(live_http: httpx.Client) -> None:
    headers = live_api_headers()
    r = live_http.get("/v1/catalog", headers=headers)
    assert r.status_code != 401, r.text
    assert r.status_code == 200
    assert isinstance(r.json().get("tables"), list)


def test_e2e_workspace_settings(live_http: httpx.Client) -> None:
    headers = live_api_headers()
    r = live_http.get("/v1/workspace/settings", headers=headers)
    assert r.status_code != 401, r.text
    assert r.status_code == 200
    body = r.json()
    assert "settings" in body
    assert "schema" in body


def test_e2e_catalog_descriptions_survive_sync(
    live_http: httpx.Client,
    catalog_table_name: str,
) -> None:
    """PATCH description → Postgres/file store → POST sync → GET catalog keeps text."""
    headers = live_api_headers()
    catalog = live_http.get("/v1/catalog", headers=headers)
    assert catalog.status_code == 200

    patch = live_http.patch(
        "/v1/catalog/descriptions",
        json={
            "tables": [
                {
                    "name": catalog_table_name,
                    "schema": "public",
                    "table_description": "E2E catalog override",
                }
            ]
        },
        headers=headers,
    )
    assert patch.status_code == 200, patch.text

    sync = live_http.post("/v1/catalog/sync", headers=headers)
    assert sync.status_code == 200, sync.text

    after = live_http.get("/v1/catalog", headers=headers)
    assert after.status_code == 200
    table = next(t for t in after.json()["tables"] if t.get("name") == catalog_table_name)
    assert table.get("table_description") == "E2E catalog override"


def test_e2e_chat_json(live_http_llm: httpx.Client) -> None:
    headers = live_api_headers()
    try:
        r = post_chat_json(
            live_http_llm,
            message="List one table name only.",
            headers=headers,
        )
    except httpx.RequestError as exc:
        skip_if_llm_unavailable(exc=exc)
        raise

    assert r.status_code != 401, r.text
    skip_if_llm_unavailable(status_code=r.status_code, body=r.text)
    if r.status_code == 400:
        pytest.fail(f"Unexpected 400 from chat on benign prompt: {r.text}")
    assert r.status_code == 200, r.text
    assert_chat_json_body(r.json())


def test_e2e_live_query(live_http_llm: httpx.Client, catalog_table_name: str) -> None:
    """Natural language query against a catalog table."""
    headers = live_api_headers()
    try:
        response = live_http_llm.post(
            "/v1/query",
            json={"query": f"Show me 2 rows from {catalog_table_name}"},
            headers=headers,
        )
    except httpx.RequestError as exc:
        skip_if_llm_unavailable(exc=exc)
        raise

    assert response.status_code != 401, f"Unexpected 401 (auth regression): {response.text}"
    skip_if_llm_unavailable(status_code=response.status_code, body=response.text)
    detail = ""
    try:
        detail = str(response.json().get("detail", ""))
    except Exception:
        detail = response.text
    if response.status_code == 400 and "out_of_scope" in detail:
        pytest.fail(f"Benign query incorrectly marked out of scope: {response.text}")
    if response.status_code == 400:
        pytest.fail(f"Unexpected 400 from query: {response.text}")
    assert response.status_code == 200, response.text
    assert_query_json_body(response.json())
