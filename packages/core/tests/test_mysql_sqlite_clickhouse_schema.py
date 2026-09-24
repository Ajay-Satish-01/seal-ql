"""Tests for MySQL, SQLite, and ClickHouse schema introspectors."""

from __future__ import annotations

import importlib.util
from typing import Any
from unittest.mock import MagicMock

import pytest
from seal_core.reasoning.models import DatabaseCapabilities
from seal_core.schema.clickhouse import (
    ClickHouseIntrospector,
    _normalize_clickhouse_type,
)
from seal_core.schema.introspector import get_introspector
from seal_core.schema.models import ColumnType, TableKind
from seal_core.schema.mysql import MySQLIntrospector, _normalize_mysql_type
from seal_core.schema.sqlite import SQLiteIntrospector, _normalize_sqlite_type


class TestGetIntrospector:
    def test_mysql(self) -> None:
        intro = get_introspector("mysql", "mysql://localhost/db")
        assert isinstance(intro, MySQLIntrospector)

    def test_mariadb_alias(self) -> None:
        intro = get_introspector("mariadb", "mariadb://localhost/db")
        assert isinstance(intro, MySQLIntrospector)

    def test_sqlite(self) -> None:
        intro = get_introspector("sqlite", ":memory:")
        assert isinstance(intro, SQLiteIntrospector)

    def test_clickhouse(self) -> None:
        intro = get_introspector("clickhouse", "clickhouse://localhost:8123/default")
        assert isinstance(intro, ClickHouseIntrospector)

    def test_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported dialect"):
            get_introspector("oracle", "oracle://localhost/db")


class TestTypeNormalization:
    def test_mysql_types(self) -> None:
        assert _normalize_mysql_type("int") == ColumnType.INTEGER
        assert _normalize_mysql_type("varchar") == ColumnType.STRING
        assert _normalize_mysql_type("datetime") == ColumnType.TIMESTAMP
        assert _normalize_mysql_type("json") == ColumnType.JSON
        assert _normalize_mysql_type("decimal") == ColumnType.NUMERIC

    def test_sqlite_types(self) -> None:
        assert _normalize_sqlite_type("INTEGER") == ColumnType.INTEGER
        assert _normalize_sqlite_type("VARCHAR(100)") == ColumnType.STRING
        assert _normalize_sqlite_type("REAL") == ColumnType.FLOAT
        assert _normalize_sqlite_type("") == ColumnType.OTHER

    def test_clickhouse_types(self) -> None:
        assert _normalize_clickhouse_type("Int64") == ColumnType.INTEGER
        assert _normalize_clickhouse_type("Nullable(String)") == ColumnType.STRING
        assert _normalize_clickhouse_type("LowCardinality(String)") == ColumnType.STRING
        assert _normalize_clickhouse_type("DateTime64(3)") == ColumnType.TIMESTAMP
        assert _normalize_clickhouse_type("Array(Int32)") == ColumnType.ARRAY
        assert _normalize_clickhouse_type("Decimal(18, 4)") == ColumnType.NUMERIC


class TestMySQLIntrospectorMocked:
    @pytest.mark.asyncio
    async def test_introspect_tables_columns_pks_fks(self) -> None:
        intro = MySQLIntrospector("mysql://localhost/app")

        async def fake_query(sql: str) -> list[dict[str, Any]]:
            lowered = sql.lower()
            if "information_schema.tables" in lowered:
                return [
                    {
                        "table_schema": "app",
                        "table_name": "users",
                        "table_type": "BASE TABLE",
                        "table_rows": 10,
                        "table_comment": "People",
                    },
                    {
                        "table_schema": "app",
                        "table_name": "orders",
                        "table_type": "BASE TABLE",
                        "table_rows": 3,
                        "table_comment": "",
                    },
                ]
            if "information_schema.columns" in lowered:
                return [
                    {
                        "table_schema": "app",
                        "table_name": "users",
                        "column_name": "id",
                        "data_type": "int",
                        "column_type": "int(11)",
                        "is_nullable": "NO",
                        "column_default": None,
                        "column_key": "PRI",
                        "column_comment": "",
                    },
                    {
                        "table_schema": "app",
                        "table_name": "users",
                        "column_name": "email",
                        "data_type": "varchar",
                        "column_type": "varchar(255)",
                        "is_nullable": "YES",
                        "column_default": None,
                        "column_key": "",
                        "column_comment": "login",
                    },
                    {
                        "table_schema": "app",
                        "table_name": "orders",
                        "column_name": "id",
                        "data_type": "int",
                        "column_type": "int",
                        "is_nullable": "NO",
                        "column_default": None,
                        "column_key": "PRI",
                        "column_comment": "",
                    },
                    {
                        "table_schema": "app",
                        "table_name": "orders",
                        "column_name": "user_id",
                        "data_type": "int",
                        "column_type": "int",
                        "is_nullable": "NO",
                        "column_default": None,
                        "column_key": "MUL",
                        "column_comment": "",
                    },
                ]
            if "key_column_usage" in lowered:
                return [
                    {
                        "constraint_name": "fk_orders_user",
                        "from_schema": "app",
                        "from_table": "orders",
                        "from_column": "user_id",
                        "to_schema": "app",
                        "to_table": "users",
                        "to_column": "id",
                    }
                ]
            raise AssertionError(f"unexpected SQL: {sql}")

        intro._query = fake_query  # type: ignore[assignment]
        schema = await intro.introspect()

        assert schema.dialect == "mysql"
        users = schema.get_table("users")
        assert users is not None
        assert users.schema_name == "app"
        assert users.description == "People"
        assert users.get_column("id") is not None
        assert users.get_column("id").is_primary_key is True
        assert users.get_column("email").nullable is True
        assert users.get_column("email").description == "login"
        assert len(schema.relationships) == 1
        assert schema.relationships[0].from_table == "orders"
        assert schema.relationships[0].to_table == "users"


class TestSQLiteIntrospector:
    pytestmark = pytest.mark.skipif(
        importlib.util.find_spec("aiosqlite") is None,
        reason="sqlite extra (aiosqlite) is not installed",
    )
    @pytest.mark.asyncio
    async def test_introspect_empty_memory(self) -> None:
        intro = SQLiteIntrospector(":memory:")
        schema = await intro.introspect()
        await intro.close()
        assert schema.dialect == "sqlite"
        assert schema.has_timescaledb is False

    @pytest.mark.asyncio
    async def test_introspect_tables_pk_fk(self, tmp_path: Any) -> None:
        db_path = tmp_path / "app.db"
        intro = SQLiteIntrospector(str(db_path))
        conn = await intro._get_conn()
        await conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount REAL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        await conn.execute("INSERT INTO users VALUES (1, 'Alice', 'a@example.com')")
        await conn.commit()

        schema = await intro.introspect()
        await intro.close()

        users = schema.get_table("users")
        assert users is not None
        assert users.schema_name == "main"
        assert users.get_column("id").is_primary_key is True
        assert users.get_column("name").nullable is False
        assert users.row_count == 1

        orders = schema.get_table("orders")
        assert orders is not None
        assert any(
            rel.from_table == "orders" and rel.to_table == "users" for rel in schema.relationships
        )

    @pytest.mark.asyncio
    async def test_file_url_normalized_path(self, tmp_path: Any) -> None:
        db_path = tmp_path / "file.db"
        intro = SQLiteIntrospector(str(db_path))
        conn = await intro._get_conn()
        await conn.execute("CREATE TABLE t (id INTEGER)")
        await conn.commit()
        schema = await intro.introspect()
        await intro.close()
        assert schema.get_table("t") is not None


class TestClickHouseIntrospectorMocked:
    @pytest.mark.asyncio
    async def test_introspect_system_tables(self) -> None:
        intro = ClickHouseIntrospector("clickhouse://localhost:8123/default")

        def fake_query(sql: str) -> list[dict[str, Any]]:
            lowered = sql.lower()
            if "system.tables" in lowered:
                return [
                    {
                        "database": "analytics",
                        "name": "events",
                        "engine": "MergeTree",
                        "total_rows": 1000,
                        "comment": "raw events",
                    },
                    {
                        "database": "analytics",
                        "name": "events_daily",
                        "engine": "MaterializedView",
                        "total_rows": 30,
                        "comment": "",
                    },
                ]
            if "system.columns" in lowered:
                return [
                    {
                        "database": "analytics",
                        "table": "events",
                        "name": "ts",
                        "type": "DateTime",
                        "position": 1,
                        "default_kind": "",
                        "default_expression": "",
                        "comment": "",
                        "is_in_primary_key": 1,
                    },
                    {
                        "database": "analytics",
                        "table": "events",
                        "name": "payload",
                        "type": "Nullable(String)",
                        "position": 2,
                        "default_kind": "",
                        "default_expression": "",
                        "comment": "json blob",
                        "is_in_primary_key": 0,
                    },
                    {
                        "database": "analytics",
                        "table": "events_daily",
                        "name": "day",
                        "type": "Date",
                        "position": 1,
                        "default_kind": "",
                        "default_expression": "",
                        "comment": "",
                        "is_in_primary_key": 1,
                    },
                ]
            raise AssertionError(f"unexpected SQL: {sql}")

        intro._query = fake_query  # type: ignore[assignment]
        intro._client = MagicMock()
        schema = await intro.introspect()

        assert schema.dialect == "clickhouse"
        events = schema.get_table("events")
        assert events is not None
        assert events.kind == TableKind.TABLE
        assert events.get_column("ts").is_primary_key is True
        assert events.get_column("payload").nullable is True
        daily = schema.get_table("events_daily")
        assert daily is not None
        assert daily.kind == TableKind.MATERIALIZED_VIEW
        assert schema.relationships == []


class TestDatabaseCapabilities:
    def test_mysql_json(self) -> None:
        caps = DatabaseCapabilities.from_bundle(database_id="ops", dialect="mysql")
        assert caps.provider == "mysql"
        assert caps.supports_json_columns is True

    def test_sqlite_provider(self) -> None:
        caps = DatabaseCapabilities.from_bundle(database_id="local", dialect="sqlite")
        assert caps.provider == "sqlite"
        assert caps.supports_json_columns is False

    def test_clickhouse_json(self) -> None:
        caps = DatabaseCapabilities.from_bundle(database_id="olap", dialect="clickhouse")
        assert caps.provider == "clickhouse"
        assert caps.supports_json_columns is True
        assert caps.supports_time_series is True
