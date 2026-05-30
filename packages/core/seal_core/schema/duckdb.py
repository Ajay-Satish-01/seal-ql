"""DuckDB schema introspector.

DuckDB is used as a zero-config, in-process database for local development
and demos. It supports information_schema for standard introspection.
"""

from __future__ import annotations

import logging

import duckdb

from seal_core.schema.models import (
    ColumnInfo,
    ColumnType,
    DatabaseSchema,
    RelationshipInfo,
    TableKind,
    TableSchema,
)

logger = logging.getLogger(__name__)

# ============================================================
# DuckDB type → normalized ColumnType mapping
# ============================================================

_DUCKDB_TYPE_MAP: dict[str, ColumnType] = {
    "integer": ColumnType.INTEGER,
    "bigint": ColumnType.INTEGER,
    "smallint": ColumnType.INTEGER,
    "tinyint": ColumnType.INTEGER,
    "hugeint": ColumnType.INTEGER,
    "ubigint": ColumnType.INTEGER,
    "uinteger": ColumnType.INTEGER,
    "usmallint": ColumnType.INTEGER,
    "utinyint": ColumnType.INTEGER,
    "float": ColumnType.FLOAT,
    "double": ColumnType.FLOAT,
    "real": ColumnType.FLOAT,
    "decimal": ColumnType.NUMERIC,
    "numeric": ColumnType.NUMERIC,
    "boolean": ColumnType.BOOLEAN,
    "varchar": ColumnType.STRING,
    "text": ColumnType.STRING,
    "char": ColumnType.STRING,
    "blob": ColumnType.STRING,
    "uuid": ColumnType.STRING,
    "date": ColumnType.DATE,
    "timestamp": ColumnType.TIMESTAMP,
    "timestamp with time zone": ColumnType.TIMESTAMP,
    "timestamptz": ColumnType.TIMESTAMP,
    "json": ColumnType.JSON,
}


def _normalize_duckdb_type(raw_type: str) -> ColumnType:
    """Map a raw DuckDB type string to our normalized ColumnType."""
    lower = raw_type.lower().strip()
    if lower in _DUCKDB_TYPE_MAP:
        return _DUCKDB_TYPE_MAP[lower]
    # Array types
    if "[]" in lower or lower.startswith("list"):
        return ColumnType.ARRAY
    # Struct / Map
    if lower.startswith("struct") or lower.startswith("map"):
        return ColumnType.JSON
    # Decimal with precision/scale
    if lower.startswith("decimal") or lower.startswith("numeric"):
        return ColumnType.NUMERIC
    # VARCHAR with length
    if lower.startswith("varchar"):
        return ColumnType.STRING
    return ColumnType.OTHER


class DuckDBIntrospector:
    """Schema introspector for DuckDB databases.

    Supports both in-memory (`:memory:`) and file-based DuckDB databases.

    Usage:
        introspector = DuckDBIntrospector(":memory:")
        schema = await introspector.introspect()
        await introspector.close()
    """

    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string
        self._conn: duckdb.DuckDBPyConnection | None = None

    def _get_conn(self) -> duckdb.DuckDBPyConnection:
        """Lazily create and return the DuckDB connection."""
        if self._conn is None:
            self._conn = duckdb.connect(self._connection_string)
        return self._conn

    async def close(self) -> None:
        """Close the DuckDB connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    async def introspect(self) -> DatabaseSchema:
        """Introspect the full DuckDB schema.

        Note: DuckDB operations are synchronous under the hood since DuckDB
        is in-process. The async interface is for protocol compatibility.
        """
        conn = self._get_conn()

        # Get tables and views
        tables_rows = conn.execute("""
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            ORDER BY table_schema, table_name
        """).fetchall()

        # Get columns
        columns_rows = conn.execute("""
            SELECT
                table_schema,
                table_name,
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            ORDER BY table_schema, table_name, ordinal_position
        """).fetchall()

        # Get primary keys via duckdb_constraints()
        pk_rows: list[tuple] = []
        try:
            pk_rows = conn.execute("""
                SELECT
                    schema_name,
                    table_name,
                    unnest(constraint_column_names) AS column_name
                FROM duckdb_constraints()
                WHERE constraint_type = 'PRIMARY KEY'
            """).fetchall()
        except Exception:
            logger.debug("Could not query duckdb_constraints() for primary keys")

        # Build lookups
        pk_lookup: dict[str, set[str]] = {}
        for schema_name, table_name, col_name in pk_rows:
            key = f"{schema_name}.{table_name}"
            pk_lookup.setdefault(key, set()).add(col_name)

        columns_lookup: dict[str, list[ColumnInfo]] = {}
        for schema_name, table_name, col_name, data_type, is_nullable, col_default in columns_rows:
            key = f"{schema_name}.{table_name}"
            col = ColumnInfo(
                name=col_name,
                data_type=data_type,
                normalized_type=_normalize_duckdb_type(data_type),
                nullable=is_nullable == "YES",
                is_primary_key=col_name in pk_lookup.get(key, set()),
                default_value=col_default,
            )
            columns_lookup.setdefault(key, []).append(col)

        # Get approximate row counts
        row_counts: dict[str, int] = {}
        for schema_name, table_name, table_type in tables_rows:
            if table_type == "BASE TABLE":
                try:
                    result = conn.execute(
                        f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}"'
                    ).fetchone()
                    if result:
                        row_counts[f"{schema_name}.{table_name}"] = result[0]
                except Exception:
                    pass

        # Assemble tables
        tables: list[TableSchema] = []
        for schema_name, table_name, table_type in tables_rows:
            key = f"{schema_name}.{table_name}"
            kind = TableKind.VIEW if table_type == "VIEW" else TableKind.TABLE

            table = TableSchema(
                name=table_name,
                schema_name=schema_name,
                kind=kind,
                columns=columns_lookup.get(key, []),
                row_count=row_counts.get(key),
            )
            tables.append(table)

        # DuckDB doesn't have foreign keys in the traditional sense,
        # but we try to get them from duckdb_constraints()
        relationships: list[RelationshipInfo] = []
        try:
            fk_rows = conn.execute("""
                SELECT
                    schema_name,
                    table_name,
                    unnest(constraint_column_names) AS from_column,
                    constraint_text
                FROM duckdb_constraints()
                WHERE constraint_type = 'FOREIGN KEY'
            """).fetchall()
            # Note: Parsing FK targets from constraint_text is complex,
            # so we log and skip for now. DuckDB FK support is limited.
            if fk_rows:
                logger.info(f"Found {len(fk_rows)} foreign key constraints in DuckDB")
        except Exception:
            pass

        return DatabaseSchema(
            dialect="duckdb",
            tables=tables,
            relationships=relationships,
            has_timescaledb=False,
        )
