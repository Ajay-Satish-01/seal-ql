"""MySQL / MariaDB schema introspector.

Discovers tables, views, columns, primary keys, and foreign keys via
``information_schema``. System schemas (mysql, performance_schema, sys,
information_schema) are excluded.
"""

from __future__ import annotations

from typing import Any

from seal_core.database.config import parse_network_url
from seal_core.schema.models import (
    ColumnInfo,
    ColumnType,
    DatabaseSchema,
    RelationshipInfo,
    TableKind,
    TableSchema,
)

_MYSQL_TYPE_MAP: dict[str, ColumnType] = {
    "tinyint": ColumnType.INTEGER,
    "smallint": ColumnType.INTEGER,
    "mediumint": ColumnType.INTEGER,
    "int": ColumnType.INTEGER,
    "integer": ColumnType.INTEGER,
    "bigint": ColumnType.INTEGER,
    "year": ColumnType.INTEGER,
    "float": ColumnType.FLOAT,
    "double": ColumnType.FLOAT,
    "real": ColumnType.FLOAT,
    "decimal": ColumnType.NUMERIC,
    "numeric": ColumnType.NUMERIC,
    "bit": ColumnType.BOOLEAN,
    "bool": ColumnType.BOOLEAN,
    "boolean": ColumnType.BOOLEAN,
    "char": ColumnType.STRING,
    "varchar": ColumnType.STRING,
    "tinytext": ColumnType.STRING,
    "text": ColumnType.STRING,
    "mediumtext": ColumnType.STRING,
    "longtext": ColumnType.STRING,
    "enum": ColumnType.STRING,
    "set": ColumnType.STRING,
    "binary": ColumnType.STRING,
    "varbinary": ColumnType.STRING,
    "tinyblob": ColumnType.STRING,
    "blob": ColumnType.STRING,
    "mediumblob": ColumnType.STRING,
    "longblob": ColumnType.STRING,
    "uuid": ColumnType.STRING,
    "date": ColumnType.DATE,
    "datetime": ColumnType.TIMESTAMP,
    "timestamp": ColumnType.TIMESTAMP,
    "time": ColumnType.TIMESTAMP,
    "json": ColumnType.JSON,
}


def _normalize_mysql_type(raw_type: str) -> ColumnType:
    """Map a raw MySQL/MariaDB type string to our normalized ColumnType."""
    lower = raw_type.lower().strip()
    if lower in _MYSQL_TYPE_MAP:
        return _MYSQL_TYPE_MAP[lower]
    for key, col_type in _MYSQL_TYPE_MAP.items():
        if lower.startswith(key):
            return col_type
    return ColumnType.OTHER


_SCHEMA_FILTER = "NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')"

_TABLES_QUERY = f"""
SELECT
    table_schema AS table_schema,
    table_name AS table_name,
    table_type AS table_type,
    table_rows AS table_rows,
    table_comment AS table_comment
FROM information_schema.tables
WHERE table_schema {_SCHEMA_FILTER}
  AND table_type IN ('BASE TABLE', 'VIEW')
ORDER BY table_schema, table_name
"""

_COLUMNS_QUERY = f"""
SELECT
    table_schema AS table_schema,
    table_name AS table_name,
    column_name AS column_name,
    data_type AS data_type,
    column_type AS column_type,
    is_nullable AS is_nullable,
    column_default AS column_default,
    column_key AS column_key,
    column_comment AS column_comment
FROM information_schema.columns
WHERE table_schema {_SCHEMA_FILTER}
ORDER BY table_schema, table_name, ordinal_position
"""

_FOREIGN_KEYS_QUERY = f"""
SELECT
    kcu.constraint_name AS constraint_name,
    kcu.table_schema AS from_schema,
    kcu.table_name AS from_table,
    kcu.column_name AS from_column,
    kcu.referenced_table_schema AS to_schema,
    kcu.referenced_table_name AS to_table,
    kcu.referenced_column_name AS to_column
FROM information_schema.key_column_usage kcu
WHERE kcu.referenced_table_name IS NOT NULL
  AND kcu.table_schema {_SCHEMA_FILTER}
"""


class MySQLIntrospector:
    """Schema introspector for MySQL and MariaDB.

    Usage:
        introspector = MySQLIntrospector("mysql://user:pass@host:3306/db")
        schema = await introspector.introspect()
        await introspector.close()
    """

    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string
        self._pool: Any = None

    async def _get_pool(self) -> Any:
        """Lazily create and return the aiomysql connection pool."""
        if self._pool is None:
            try:
                import aiomysql
            except ImportError as exc:
                raise ImportError(
                    "MySQL/MariaDB support requires the mysql extra "
                    "(uv sync --extra mysql, or pip install 'seal-core[mysql]')."
                ) from exc

            params = parse_network_url(
                self._connection_string,
                default_port=3306,
                default_user="root",
            )
            self._pool = await aiomysql.create_pool(
                host=params.host,
                port=params.port,
                user=params.user,
                password=params.password,
                db=params.database or None,
                minsize=1,
                maxsize=5,
                autocommit=True,
                charset="utf8mb4",
            )
        return self._pool

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    async def _query(self, sql: str) -> list[dict[str, Any]]:
        """Run a read-only information_schema query and return dict rows."""
        try:
            import aiomysql
        except ImportError as exc:
            raise ImportError(
                "MySQL/MariaDB support requires the mysql extra "
                "(uv sync --extra mysql, or pip install 'seal-core[mysql]')."
            ) from exc

        pool = await self._get_pool()
        async with pool.acquire() as conn, conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql)
            rows = await cur.fetchall()
        return [_lowercase_row_keys(dict(row)) for row in rows]

    async def introspect(self) -> DatabaseSchema:
        """Introspect tables, columns, PKs, and FKs from information_schema."""
        tables_rows = await self._query(_TABLES_QUERY)
        columns_rows = await self._query(_COLUMNS_QUERY)
        fk_rows = await self._query(_FOREIGN_KEYS_QUERY)

        columns_lookup: dict[str, list[ColumnInfo]] = {}
        for row in columns_rows:
            row = _lowercase_row_keys(row)
            key = f"{row['table_schema']}.{row['table_name']}"
            raw_type = row.get("column_type") or row.get("data_type") or ""
            col = ColumnInfo(
                name=row["column_name"],
                data_type=str(raw_type),
                normalized_type=_normalize_mysql_type(str(row.get("data_type") or raw_type)),
                nullable=str(row.get("is_nullable", "YES")).upper() == "YES",
                is_primary_key=str(row.get("column_key", "")).upper() == "PRI",
                default_value=_optional_str(row.get("column_default")),
                description=_optional_str(row.get("column_comment")),
            )
            columns_lookup.setdefault(key, []).append(col)

        tables: list[TableSchema] = []
        for row in tables_rows:
            row = _lowercase_row_keys(row)
            schema_name = row["table_schema"]
            table_name = row["table_name"]
            key = f"{schema_name}.{table_name}"
            kind = TableKind.VIEW if str(row.get("table_type")) == "VIEW" else TableKind.TABLE
            row_count = row.get("table_rows")
            table = TableSchema(
                name=table_name,
                schema_name=schema_name,
                kind=kind,
                columns=columns_lookup.get(key, []),
                row_count=int(row_count) if row_count is not None else None,
                description=_optional_str(row.get("table_comment")),
            )
            tables.append(table)

        relationships = [
            RelationshipInfo(
                from_table=row["from_table"],
                from_column=row["from_column"],
                to_table=row["to_table"],
                to_column=row["to_column"],
                constraint_name=_optional_str(row.get("constraint_name")),
            )
            for row in (_lowercase_row_keys(raw) for raw in fk_rows)
            if row.get("from_table") and row.get("to_table")
        ]

        return DatabaseSchema(
            dialect="mysql",
            tables=tables,
            relationships=relationships,
            has_timescaledb=False,
        )


def _lowercase_row_keys(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize information_schema keys (MySQL 8 may return UPPERCASE)."""
    return {str(key).lower(): value for key, value in row.items()}


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
