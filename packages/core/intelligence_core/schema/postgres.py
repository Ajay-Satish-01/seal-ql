"""PostgreSQL + TimescaleDB schema introspector.

Discovers all queryable objects in a Postgres database:
  - Tables (via information_schema.tables)
  - Views (via information_schema.views)
  - Materialized views (via pg_matviews — NOT in information_schema)
  - Foreign key relationships
  - TimescaleDB hypertables (via timescaledb_information.hypertables)
  - Continuous aggregates (via timescaledb_information.continuous_aggregates)

TimescaleDB introspection is graceful — if the extension isn't installed,
those queries are simply skipped.
"""

from __future__ import annotations

import logging
from typing import Any

import asyncpg

from intelligence_core.schema.models import (
    ColumnInfo,
    ColumnType,
    ContinuousAggregateInfo,
    DatabaseSchema,
    HypertableInfo,
    RelationshipInfo,
    TableKind,
    TableSchema,
)

logger = logging.getLogger(__name__)

# ============================================================
# SQL type → normalized ColumnType mapping
# ============================================================

_PG_TYPE_MAP: dict[str, ColumnType] = {
    "integer": ColumnType.INTEGER,
    "bigint": ColumnType.INTEGER,
    "smallint": ColumnType.INTEGER,
    "serial": ColumnType.INTEGER,
    "bigserial": ColumnType.INTEGER,
    "real": ColumnType.FLOAT,
    "double precision": ColumnType.FLOAT,
    "numeric": ColumnType.NUMERIC,
    "decimal": ColumnType.NUMERIC,
    "boolean": ColumnType.BOOLEAN,
    "character varying": ColumnType.STRING,
    "varchar": ColumnType.STRING,
    "character": ColumnType.STRING,
    "char": ColumnType.STRING,
    "text": ColumnType.STRING,
    "uuid": ColumnType.STRING,
    "date": ColumnType.DATE,
    "timestamp without time zone": ColumnType.TIMESTAMP,
    "timestamp with time zone": ColumnType.TIMESTAMP,
    "timestamptz": ColumnType.TIMESTAMP,
    "json": ColumnType.JSON,
    "jsonb": ColumnType.JSON,
    "array": ColumnType.ARRAY,
    "user-defined": ColumnType.OTHER,
}


def _normalize_pg_type(raw_type: str) -> ColumnType:
    """Map a raw Postgres type string to our normalized ColumnType."""
    lower = raw_type.lower().strip()
    # Direct match
    if lower in _PG_TYPE_MAP:
        return _PG_TYPE_MAP[lower]
    # Check for array types (e.g., "integer[]", "_int4")
    if lower.endswith("[]") or lower.startswith("_"):
        return ColumnType.ARRAY
    # Check for partial matches (e.g., "character varying(100)")
    for key, col_type in _PG_TYPE_MAP.items():
        if lower.startswith(key):
            return col_type
    return ColumnType.OTHER


# ============================================================
# Introspection queries
# ============================================================

# Tables and views from information_schema
_TABLES_QUERY = """
SELECT
    table_schema,
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema', '_timescaledb_catalog',
                           '_timescaledb_internal', '_timescaledb_config', '_timescaledb_cache',
                           'timescaledb_information', 'timescaledb_experimental')
  AND table_type IN ('BASE TABLE', 'VIEW')
ORDER BY table_schema, table_name;
"""

# Materialized views — NOT in information_schema, must use pg_matviews
_MATVIEWS_QUERY = """
SELECT
    schemaname AS schema_name,
    matviewname AS view_name,
    ispopulated AS is_populated
FROM pg_matviews
WHERE schemaname NOT IN ('pg_catalog', 'information_schema', '_timescaledb_catalog',
                         '_timescaledb_internal', '_timescaledb_config')
ORDER BY schemaname, matviewname;
"""

# Columns for regular tables and views
_COLUMNS_QUERY = """
SELECT
    c.table_schema,
    c.table_name,
    c.column_name,
    c.data_type,
    c.udt_name,
    c.is_nullable,
    c.column_default,
    c.character_maximum_length,
    pgd.description AS column_comment
FROM information_schema.columns c
LEFT JOIN pg_catalog.pg_statio_all_tables st
    ON st.schemaname = c.table_schema AND st.relname = c.table_name
LEFT JOIN pg_catalog.pg_description pgd
    ON pgd.objoid = st.relid AND pgd.objsubid = c.ordinal_position
WHERE c.table_schema NOT IN ('pg_catalog', 'information_schema', '_timescaledb_catalog',
                              '_timescaledb_internal', '_timescaledb_config', '_timescaledb_cache',
                              'timescaledb_information', 'timescaledb_experimental')
ORDER BY c.table_schema, c.table_name, c.ordinal_position;
"""

# Columns for materialized views — must use pg_attribute + pg_class
_MATVIEW_COLUMNS_QUERY = """
SELECT
    n.nspname AS table_schema,
    c.relname AS table_name,
    a.attname AS column_name,
    pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
    t.typname AS udt_name,
    CASE WHEN a.attnotnull THEN 'NO' ELSE 'YES' END AS is_nullable,
    pg_get_expr(d.adbin, d.adrelid) AS column_default,
    col_description(c.oid, a.attnum) AS column_comment
FROM pg_catalog.pg_attribute a
JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
JOIN pg_catalog.pg_type t ON a.atttypid = t.oid
LEFT JOIN pg_catalog.pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum
WHERE c.relkind = 'm'  -- materialized view
  AND a.attnum > 0      -- skip system columns
  AND NOT a.attisdropped
  AND n.nspname NOT IN ('pg_catalog', 'information_schema', '_timescaledb_catalog',
                         '_timescaledb_internal', '_timescaledb_config')
ORDER BY n.nspname, c.relname, a.attnum;
"""

# Primary keys
_PRIMARY_KEYS_QUERY = """
SELECT
    tc.table_schema,
    tc.table_name,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'PRIMARY KEY'
  AND tc.table_schema NOT IN ('pg_catalog', 'information_schema');
"""

# Foreign key relationships
_FOREIGN_KEYS_QUERY = """
SELECT
    tc.constraint_name,
    kcu.table_schema AS from_schema,
    kcu.table_name AS from_table,
    kcu.column_name AS from_column,
    ccu.table_schema AS to_schema,
    ccu.table_name AS to_table,
    ccu.column_name AS to_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
    ON tc.constraint_name = ccu.constraint_name
    AND tc.table_schema = ccu.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY';
"""

# Approximate row counts (fast — uses pg_stat, not COUNT(*))
_ROW_COUNTS_QUERY = """
SELECT
    schemaname AS table_schema,
    relname AS table_name,
    n_live_tup AS row_count
FROM pg_stat_user_tables;
"""

# Check if TimescaleDB extension is installed
_TIMESCALEDB_CHECK_QUERY = """
SELECT EXISTS(
    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
) AS is_installed;
"""

# TimescaleDB hypertables
_HYPERTABLES_QUERY = """
SELECT
    hypertable_schema,
    hypertable_name,
    -- The time dimension column
    (SELECT column_name
     FROM timescaledb_information.dimensions d
     WHERE d.hypertable_schema = h.hypertable_schema
       AND d.hypertable_name = h.hypertable_name
       AND d.column_type IN (
           'timestamp with time zone',
           'timestamp without time zone',
           'date', 'bigint', 'integer'
       )
     ORDER BY d.dimension_number
     LIMIT 1) AS time_column,
    num_chunks,
    compression_enabled
FROM timescaledb_information.hypertables h
WHERE hypertable_schema NOT IN ('_timescaledb_catalog', '_timescaledb_internal');
"""

# TimescaleDB continuous aggregates
_CONTINUOUS_AGGREGATES_QUERY = """
SELECT
    ca.view_schema,
    ca.view_name,
    ca.hypertable_schema || '.' || ca.hypertable_name AS source_hypertable,
    ca.view_definition
FROM timescaledb_information.continuous_aggregates ca;
"""

# Continuous aggregate refresh policies
_CAGG_POLICIES_QUERY = """
SELECT
    j.hypertable_name AS view_name,
    j.schedule_interval::text AS refresh_interval,
    jc.config->>'start_offset' AS start_offset,
    jc.config->>'end_offset' AS end_offset
FROM timescaledb_information.jobs j
JOIN pg_catalog.pg_proc p ON j.proc_name = p.proname
LEFT JOIN timescaledb_information.jobs jc ON j.job_id = jc.job_id
WHERE j.application_name LIKE '%Continuous Aggregate%'
   OR j.proc_schema = '_timescaledb_functions'
   OR j.proc_name = 'policy_refresh_continuous_aggregate';
"""


class PostgresIntrospector:
    """Schema introspector for PostgreSQL databases with optional TimescaleDB support.

    Discovers tables, views, materialized views, foreign keys, and — if the
    TimescaleDB extension is installed — hypertables and continuous aggregates.

    Usage:
        introspector = PostgresIntrospector("postgresql://user:pass@host:5432/db")
        schema = await introspector.introspect()
        await introspector.close()
    """

    def __init__(self, connection_string: str) -> None:
        # asyncpg only accepts "postgresql://" or "postgres://" schemes.
        # Strip the SQLAlchemy-style "+asyncpg" dialect suffix if present.
        self._connection_string = connection_string.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        self._pool: asyncpg.Pool | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        """Lazily create and return the connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self._connection_string,
                min_size=1,
                max_size=5,
            )
        return self._pool

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def introspect(self) -> DatabaseSchema:
        """Introspect the full Postgres database schema.

        Returns a DatabaseSchema with all tables, views, materialized views,
        relationships, and TimescaleDB metadata (if available).
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # Check TimescaleDB availability first
            has_timescaledb = await self._check_timescaledb(conn)

            # Gather all metadata concurrently where possible
            tables_rows = await conn.fetch(_TABLES_QUERY)
            matview_rows = await conn.fetch(_MATVIEWS_QUERY)
            columns_rows = await conn.fetch(_COLUMNS_QUERY)
            matview_columns_rows = await conn.fetch(_MATVIEW_COLUMNS_QUERY)
            pk_rows = await conn.fetch(_PRIMARY_KEYS_QUERY)
            fk_rows = await conn.fetch(_FOREIGN_KEYS_QUERY)
            row_count_rows = await conn.fetch(_ROW_COUNTS_QUERY)

            # TimescaleDB metadata (only if extension is present)
            hypertable_rows: list[Any] = []
            cagg_rows: list[Any] = []
            cagg_policy_rows: list[Any] = []
            if has_timescaledb:
                hypertable_rows = await conn.fetch(_HYPERTABLES_QUERY)
                cagg_rows = await conn.fetch(_CONTINUOUS_AGGREGATES_QUERY)
                try:
                    cagg_policy_rows = await conn.fetch(_CAGG_POLICIES_QUERY)
                except Exception:
                    # Refresh policy query can vary between TimescaleDB versions
                    logger.warning("Could not fetch continuous aggregate policies")

        # Build lookup structures
        pk_lookup = self._build_pk_lookup(pk_rows)
        row_count_lookup = self._build_row_count_lookup(row_count_rows)
        hypertable_lookup = self._build_hypertable_lookup(hypertable_rows)
        cagg_lookup = self._build_cagg_lookup(cagg_rows, cagg_policy_rows)

        # Build columns lookup for regular tables/views
        columns_lookup: dict[str, list[ColumnInfo]] = {}
        for row in columns_rows:
            key = f"{row['table_schema']}.{row['table_name']}"
            col = self._parse_column(row, pk_lookup.get(key, set()))
            columns_lookup.setdefault(key, []).append(col)

        # Build columns lookup for materialized views
        for row in matview_columns_rows:
            key = f"{row['table_schema']}.{row['table_name']}"
            col = self._parse_matview_column(row)
            columns_lookup.setdefault(key, []).append(col)

        # Assemble TableSchema objects
        tables: list[TableSchema] = []

        # Regular tables and views
        for row in tables_rows:
            schema_name = row["table_schema"]
            table_name = row["table_name"]
            key = f"{schema_name}.{table_name}"

            # Determine kind: check if it's a hypertable or a regular table/view
            if row["table_type"] == "VIEW":
                kind = TableKind.VIEW
            elif key in hypertable_lookup:
                kind = TableKind.HYPERTABLE
            else:
                kind = TableKind.TABLE

            table = TableSchema(
                name=table_name,
                schema_name=schema_name,
                kind=kind,
                columns=columns_lookup.get(key, []),
                row_count=row_count_lookup.get(key),
                hypertable_info=hypertable_lookup.get(key),
            )
            tables.append(table)

        # Materialized views (and continuous aggregates)
        for row in matview_rows:
            schema_name = row["schema_name"]
            view_name = row["view_name"]
            key = f"{schema_name}.{view_name}"

            if key in cagg_lookup:
                kind = TableKind.CONTINUOUS_AGGREGATE
                ca_info = cagg_lookup[key]
            else:
                kind = TableKind.MATERIALIZED_VIEW
                ca_info = None

            table = TableSchema(
                name=view_name,
                schema_name=schema_name,
                kind=kind,
                columns=columns_lookup.get(key, []),
                row_count=row_count_lookup.get(key),
                continuous_aggregate_info=ca_info,
            )
            tables.append(table)

        # Build relationships
        relationships = [
            RelationshipInfo(
                from_table=row["from_table"],
                from_column=row["from_column"],
                to_table=row["to_table"],
                to_column=row["to_column"],
                constraint_name=row["constraint_name"],
            )
            for row in fk_rows
        ]

        return DatabaseSchema(
            dialect="postgres",
            tables=tables,
            relationships=relationships,
            has_timescaledb=has_timescaledb,
        )

    # ============================================================
    # Private helpers
    # ============================================================

    async def _check_timescaledb(self, conn: asyncpg.Connection) -> bool:
        """Check if TimescaleDB extension is installed."""
        try:
            row = await conn.fetchrow(_TIMESCALEDB_CHECK_QUERY)
            result = row["is_installed"] if row else False
            if result:
                logger.info("TimescaleDB extension detected")
            return result
        except Exception:
            logger.debug("TimescaleDB check failed — assuming not installed")
            return False

    def _parse_column(self, row: Any, pk_columns: set[str]) -> ColumnInfo:
        """Parse a column row from information_schema.columns."""
        raw_type = row["data_type"]
        # For user-defined types, use udt_name for more detail
        if raw_type == "USER-DEFINED":
            raw_type = row.get("udt_name", raw_type)

        return ColumnInfo(
            name=row["column_name"],
            data_type=raw_type,
            normalized_type=_normalize_pg_type(raw_type),
            nullable=row["is_nullable"] == "YES",
            is_primary_key=row["column_name"] in pk_columns,
            default_value=row["column_default"],
            description=row.get("column_comment"),
        )

    def _parse_matview_column(self, row: Any) -> ColumnInfo:
        """Parse a column row from pg_attribute (for materialized views)."""
        raw_type = row["data_type"]
        return ColumnInfo(
            name=row["column_name"],
            data_type=raw_type,
            normalized_type=_normalize_pg_type(raw_type),
            nullable=row["is_nullable"] == "YES",
            is_primary_key=False,  # Matviews don't have PKs
            default_value=row.get("column_default"),
            description=row.get("column_comment"),
        )

    def _build_pk_lookup(self, pk_rows: list[Any]) -> dict[str, set[str]]:
        """Build a lookup of schema.table → set of PK column names."""
        lookup: dict[str, set[str]] = {}
        for row in pk_rows:
            key = f"{row['table_schema']}.{row['table_name']}"
            lookup.setdefault(key, set()).add(row["column_name"])
        return lookup

    def _build_row_count_lookup(self, rows: list[Any]) -> dict[str, int]:
        """Build a lookup of schema.table → approximate row count."""
        return {f"{row['table_schema']}.{row['table_name']}": row["row_count"] for row in rows}

    def _build_hypertable_lookup(self, rows: list[Any]) -> dict[str, HypertableInfo]:
        """Build a lookup of schema.table → HypertableInfo."""
        lookup: dict[str, HypertableInfo] = {}
        for row in rows:
            key = f"{row['hypertable_schema']}.{row['hypertable_name']}"
            lookup[key] = HypertableInfo(
                time_column=row["time_column"] or "time",
                num_chunks=row.get("num_chunks"),
                compression_enabled=row.get("compression_enabled", False),
            )
        return lookup

    def _build_cagg_lookup(
        self, cagg_rows: list[Any], policy_rows: list[Any]
    ) -> dict[str, ContinuousAggregateInfo]:
        """Build a lookup of schema.view → ContinuousAggregateInfo."""
        # Build policy lookup first
        policy_lookup: dict[str, dict[str, str | None]] = {}
        for row in policy_rows:
            view_name = row.get("view_name", "")
            policy_lookup[view_name] = {
                "refresh_interval": row.get("refresh_interval"),
                "start_offset": row.get("start_offset"),
                "end_offset": row.get("end_offset"),
            }

        lookup: dict[str, ContinuousAggregateInfo] = {}
        for row in cagg_rows:
            key = f"{row['view_schema']}.{row['view_name']}"
            policy = policy_lookup.get(row["view_name"], {})
            lookup[key] = ContinuousAggregateInfo(
                source_hypertable=row["source_hypertable"],
                view_definition=row.get("view_definition"),
                refresh_interval=policy.get("refresh_interval"),
                refresh_start_offset=policy.get("start_offset"),
                refresh_end_offset=policy.get("end_offset"),
            )
        return lookup
