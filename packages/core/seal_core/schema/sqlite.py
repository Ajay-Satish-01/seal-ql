"""SQLite schema introspector.

Uses ``sqlite_master``, ``PRAGMA table_info``, and ``PRAGMA foreign_key_list``.
Supports file-backed databases and ``:memory:``.
"""

from __future__ import annotations

import logging
from typing import Any

from seal_core.database.config import sqlite_connect_args
from seal_core.schema.models import (
    ColumnInfo,
    ColumnType,
    DatabaseSchema,
    RelationshipInfo,
    TableKind,
    TableSchema,
)

logger = logging.getLogger(__name__)

_SQLITE_TYPE_MAP: dict[str, ColumnType] = {
    "int": ColumnType.INTEGER,
    "integer": ColumnType.INTEGER,
    "tinyint": ColumnType.INTEGER,
    "smallint": ColumnType.INTEGER,
    "mediumint": ColumnType.INTEGER,
    "bigint": ColumnType.INTEGER,
    "int2": ColumnType.INTEGER,
    "int8": ColumnType.INTEGER,
    "real": ColumnType.FLOAT,
    "double": ColumnType.FLOAT,
    "double precision": ColumnType.FLOAT,
    "float": ColumnType.FLOAT,
    "numeric": ColumnType.NUMERIC,
    "decimal": ColumnType.NUMERIC,
    "boolean": ColumnType.BOOLEAN,
    "bool": ColumnType.BOOLEAN,
    "character": ColumnType.STRING,
    "varchar": ColumnType.STRING,
    "varying character": ColumnType.STRING,
    "nchar": ColumnType.STRING,
    "native character": ColumnType.STRING,
    "nvarchar": ColumnType.STRING,
    "text": ColumnType.STRING,
    "clob": ColumnType.STRING,
    "blob": ColumnType.STRING,
    "date": ColumnType.DATE,
    "datetime": ColumnType.TIMESTAMP,
    "timestamp": ColumnType.TIMESTAMP,
    "json": ColumnType.JSON,
}


def _normalize_sqlite_type(raw_type: str) -> ColumnType:
    """Map a declared SQLite type affinity string to ColumnType."""
    lower = raw_type.lower().strip()
    if not lower:
        return ColumnType.OTHER
    if lower in _SQLITE_TYPE_MAP:
        return _SQLITE_TYPE_MAP[lower]
    # SQLite affinity rules (simplified): INT → integer, CHAR/CLOB/TEXT → string, etc.
    if "int" in lower:
        return ColumnType.INTEGER
    if "char" in lower or "clob" in lower or "text" in lower:
        return ColumnType.STRING
    if "blob" in lower:
        return ColumnType.STRING
    if "real" in lower or "floa" in lower or "doub" in lower:
        return ColumnType.FLOAT
    if lower.startswith("decimal") or lower.startswith("numeric"):
        return ColumnType.NUMERIC
    if lower.startswith("json"):
        return ColumnType.JSON
    return ColumnType.OTHER


class SQLiteIntrospector:
    """Schema introspector for SQLite databases.

    Usage:
        introspector = SQLiteIntrospector("data/app.db")
        schema = await introspector.introspect()
        await introspector.close()
    """

    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string
        self._conn: Any = None

    async def _get_conn(self) -> Any:
        """Lazily create and return an aiosqlite connection."""
        if self._conn is None:
            try:
                import aiosqlite
            except ImportError as exc:
                raise ImportError(
                    "SQLite support requires the sqlite extra "
                    "(uv sync --extra sqlite, or pip install 'seal-core[sqlite]')."
                ) from exc

            database, uri = sqlite_connect_args(self._connection_string)
            self._conn = await aiosqlite.connect(database, uri=uri)
            self._conn.row_factory = aiosqlite.Row
        return self._conn

    async def close(self) -> None:
        """Close the SQLite connection."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def introspect(self) -> DatabaseSchema:
        """Introspect tables, views, columns, PKs, and foreign keys."""
        conn = await self._get_conn()

        master_rows = await self._fetchall(
            conn,
            """
            SELECT name, type
            FROM sqlite_master
            WHERE type IN ('table', 'view')
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """,
        )

        tables: list[TableSchema] = []
        relationships: list[RelationshipInfo] = []

        for row in master_rows:
            name = row["name"]
            kind = TableKind.VIEW if row["type"] == "view" else TableKind.TABLE
            columns = await self._columns_for_table(conn, name)
            row_count: int | None = None
            if kind == TableKind.TABLE:
                try:
                    count_row = await self._fetchone(
                        conn, f'SELECT COUNT(*) AS n FROM "{name.replace(chr(34), chr(34) * 2)}"'
                    )
                    if count_row is not None:
                        row_count = int(count_row["n"])
                except Exception:
                    logger.debug("Could not count rows for SQLite table %s", name)

            tables.append(
                TableSchema(
                    name=name,
                    schema_name="main",
                    kind=kind,
                    columns=columns,
                    row_count=row_count,
                )
            )

            if kind == TableKind.TABLE:
                relationships.extend(await self._foreign_keys_for_table(conn, name))

        return DatabaseSchema(
            dialect="sqlite",
            tables=tables,
            relationships=relationships,
            has_timescaledb=False,
        )

    async def _columns_for_table(self, conn: Any, table_name: str) -> list[ColumnInfo]:
        rows = await self._pragma(conn, "table_info", table_name)
        columns: list[ColumnInfo] = []
        for row in rows:
            raw_type = row["type"] or ""
            pk_index = int(row["pk"] or 0)
            columns.append(
                ColumnInfo(
                    name=row["name"],
                    data_type=str(raw_type) if raw_type else "ANY",
                    normalized_type=_normalize_sqlite_type(str(raw_type)),
                    nullable=int(row["notnull"] or 0) == 0,
                    is_primary_key=pk_index > 0,
                    default_value=_optional_str(row["dflt_value"]),
                )
            )
        return columns

    async def _foreign_keys_for_table(self, conn: Any, table_name: str) -> list[RelationshipInfo]:
        rows = await self._pragma(conn, "foreign_key_list", table_name)
        rels: list[RelationshipInfo] = []
        for row in rows:
            to_table = row["table"]
            from_col = row["from"]
            to_col = row["to"]
            if not to_table or not from_col:
                continue
            rels.append(
                RelationshipInfo(
                    from_table=table_name,
                    from_column=from_col,
                    to_table=to_table,
                    to_column=to_col or "rowid",
                    constraint_name=f"fk_{table_name}_{from_col}",
                )
            )
        return rels

    async def _pragma(self, conn: Any, pragma: str, table_name: str) -> list[Any]:
        # PRAGMA identifiers cannot be bound as parameters in all SQLite builds;
        # quote the table name to avoid injection from catalog identifiers.
        quoted = table_name.replace('"', '""')
        cursor = await conn.execute(f'PRAGMA {pragma}("{quoted}")')
        return await cursor.fetchall()

    async def _fetchall(self, conn: Any, sql: str) -> list[Any]:
        cursor = await conn.execute(sql)
        return await cursor.fetchall()

    async def _fetchone(self, conn: Any, sql: str) -> Any:
        cursor = await conn.execute(sql)
        return await cursor.fetchone()


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
