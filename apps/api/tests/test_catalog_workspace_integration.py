"""Catalog + workspace integration via live API (Postgres workspace store).

Uses HTTP against the running API container so asyncpg is not shared across
pytest-asyncio and Starlette TestClient event loops.
"""

from __future__ import annotations

import httpx
from tests.shared import live_api_headers

pytest_plugins = ["tests.live_http_fixtures"]


def _table_description(body: dict, name: str) -> str | None:
    for row in body.get("tables", []):
        if row.get("name") == name:
            return row.get("table_description")
    return None


def test_live_patch_and_sync_preserve_catalog_description(
    live_http: httpx.Client,
    catalog_table_name: str,
) -> None:
    headers = live_api_headers()
    patch = live_http.patch(
        "/v1/catalog/descriptions",
        json={
            "tables": [
                {
                    "name": catalog_table_name,
                    "schema": "public",
                    "table_description": "Live HTTP integration override",
                }
            ]
        },
        headers=headers,
    )
    assert patch.status_code == 200, patch.text
    assert _table_description(patch.json(), catalog_table_name) == "Live HTTP integration override"

    sync = live_http.post("/v1/catalog/sync", headers=headers)
    assert sync.status_code == 200, sync.text

    after = live_http.get("/v1/catalog", headers=headers)
    assert after.status_code == 200, after.text
    assert _table_description(after.json(), catalog_table_name) == "Live HTTP integration override"


def test_live_workspace_settings_storage_uses_postgres(live_http: httpx.Client) -> None:
    headers = live_api_headers()
    r = live_http.get("/v1/workspace/settings", headers=headers)
    assert r.status_code == 200, r.text
    storage = r.json().get("storage") or {}
    # With DATABASE_URL=postgres and healthy DB, layered store should report postgres.
    assert storage.get("write_target") in ("postgres", "file")
