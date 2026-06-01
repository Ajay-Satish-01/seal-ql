"""Tests for DatabaseRegistry and database config loading."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from seal_core.database.config import (
    DEFAULT_DATABASE_ID,
    DatabaseConfigError,
    database_id_from_metadata,
    infer_dialect,
    is_default_database_id,
    load_database_urls,
    normalize_connection_url,
    planner_resources_for_database,
)
from seal_core.database.registry import (
    DatabaseBundle,
    DatabaseRegistry,
    UnknownDatabaseError,
    build_database_registry,
)
from seal_core.settings import clear_settings_cache, get_settings


def test_infer_dialect_postgres() -> None:
    assert infer_dialect("postgresql+asyncpg://localhost/seal") == "postgres"


def test_infer_dialect_duckdb() -> None:
    assert infer_dialect(":memory:") == "duckdb"
    assert infer_dialect("duckdb:///tmp/x.duckdb") == "duckdb"
    assert infer_dialect("/tmp/local.duckdb") == "duckdb"


def test_infer_dialect_uses_url_scheme_not_path_substrings() -> None:
    assert infer_dialect("/tmp/postgres-exports.duckdb") == "duckdb"


def test_normalize_connection_url_converts_duckdb_url_to_path() -> None:
    assert normalize_connection_url("duckdb:///tmp/x.duckdb") == "/tmp/x.duckdb"
    assert normalize_connection_url("duckdb:///:memory:") == ":memory:"
    assert normalize_connection_url(":memory:") == ":memory:"


def test_infer_dialect_rejects_unsupported_scheme() -> None:
    with pytest.raises(DatabaseConfigError, match="Unsupported"):
        infer_dialect("mysql://localhost/analytics")


def test_normalize_connection_url_rejects_remote_duckdb_url() -> None:
    with pytest.raises(DatabaseConfigError, match="local path"):
        normalize_connection_url("duckdb://localhost/tmp/x.duckdb")


def test_load_database_urls_default_only() -> None:
    entries = load_database_urls(
        database_url="postgresql+asyncpg://localhost/seal",
        seal_databases=None,
        seal_databases_path="/nonexistent/databases.yaml",
    )
    assert entries == {DEFAULT_DATABASE_ID: "postgresql+asyncpg://localhost/seal"}


def test_load_database_urls_from_json_env() -> None:
    entries = load_database_urls(
        database_url="postgresql+asyncpg://localhost/seal",
        seal_databases='{"analytics": ":memory:"}',
        seal_databases_path=None,
    )
    assert entries[DEFAULT_DATABASE_ID] == "postgresql+asyncpg://localhost/seal"
    assert entries["analytics"] == ":memory:"


def test_load_database_urls_from_yaml_file(tmp_path: Path) -> None:
    path = tmp_path / "databases.yaml"
    path.write_text(
        "databases:\n  warehouse:\n    url: duckdb:///tmp/warehouse.duckdb\n",
        encoding="utf-8",
    )
    entries = load_database_urls(
        database_url="postgresql+asyncpg://localhost/seal",
        seal_databases=None,
        seal_databases_path=str(path),
    )
    assert "warehouse" in entries
    assert entries["warehouse"] == "duckdb:///tmp/warehouse.duckdb"


def test_load_database_urls_ignores_default_override_in_yaml(tmp_path: Path) -> None:
    path = tmp_path / "databases.yaml"
    path.write_text(
        "databases:\n  default:\n    url: duckdb:///tmp/override.duckdb\n",
        encoding="utf-8",
    )
    entries = load_database_urls(
        database_url="postgresql+asyncpg://localhost/seal",
        seal_databases=None,
        seal_databases_path=str(path),
    )
    assert entries[DEFAULT_DATABASE_ID] == "postgresql+asyncpg://localhost/seal"


def test_registry_get_unknown_raises() -> None:
    bundle = DatabaseBundle(
        database_id="default",
        dialect="postgres",
        url="mock://",
        introspector=MagicMock(),
        executor=MagicMock(),
    )
    registry = DatabaseRegistry({"default": bundle})
    with pytest.raises(UnknownDatabaseError, match="analytics"):
        registry.get("analytics")


def test_registry_list_ids() -> None:
    bundle = DatabaseBundle(
        database_id="default",
        dialect="postgres",
        url="mock://",
        introspector=MagicMock(),
        executor=MagicMock(),
    )
    analytics = DatabaseBundle(
        database_id="analytics",
        dialect="duckdb",
        url=":memory:",
        introspector=MagicMock(),
        executor=MagicMock(),
    )
    registry = DatabaseRegistry({"default": bundle, "analytics": analytics})
    assert registry.list_ids() == ["analytics", "default"]


def test_load_database_urls_rejects_invalid_yaml(tmp_path: Path) -> None:
    path = tmp_path / "databases.yaml"
    path.write_text("databases:\n  bad:\n    url: :memory:\n", encoding="utf-8")
    with pytest.raises(DatabaseConfigError, match="Invalid YAML"):
        load_database_urls(
            database_url="postgresql+asyncpg://localhost/seal",
            seal_databases_path=str(path),
        )


def test_load_database_urls_rejects_empty_yaml(tmp_path: Path) -> None:
    path = tmp_path / "databases.yaml"
    path.write_text("", encoding="utf-8")
    with pytest.raises(DatabaseConfigError, match="empty"):
        load_database_urls(
            database_url="postgresql+asyncpg://localhost/seal",
            seal_databases_path=str(path),
        )


def test_load_database_urls_rejects_invalid_json_env() -> None:
    with pytest.raises(DatabaseConfigError, match="not valid JSON"):
        load_database_urls(
            database_url="postgresql+asyncpg://localhost/seal",
            seal_databases="not-json",
        )


def test_is_default_database_id() -> None:
    assert is_default_database_id("default") is True
    assert is_default_database_id("analytics") is False


def test_database_id_from_metadata() -> None:
    assert database_id_from_metadata(None) == DEFAULT_DATABASE_ID
    assert database_id_from_metadata({}) == DEFAULT_DATABASE_ID
    assert database_id_from_metadata({"database_id": "warehouse"}) == "warehouse"


def test_planner_resources_for_database() -> None:
    catalog = object()
    semantic = object()
    default_resources = planner_resources_for_database(
        "default",
        catalog=catalog,
        semantic_registry=semantic,
    )
    assert default_resources == (semantic, catalog)
    analytics_resources = planner_resources_for_database(
        "analytics",
        catalog=catalog,
        semantic_registry=semantic,
    )
    assert analytics_resources == (None, None)


def test_build_database_registry_from_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "databases.yaml"
    path.write_text(
        "databases:\n  warehouse:\n    url: duckdb:///tmp/warehouse.duckdb\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/seal")
    monkeypatch.setenv("SEAL_DATABASES_PATH", str(path))
    clear_settings_cache()
    with (
        patch("seal_core.database.registry.get_introspector") as introspector_mock,
        patch("seal_core.database.registry.QueryExecutor") as executor_mock,
    ):
        introspector_mock.return_value = MagicMock()
        executor_mock.return_value = MagicMock()
        registry = build_database_registry(get_settings())
    assert registry.list_ids() == ["default", "warehouse"]
    assert registry.get("warehouse").url == "/tmp/warehouse.duckdb"
