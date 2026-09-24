"""ClickHouse schema introspector.

Discovers tables and views via ``system.tables`` and columns via ``system.columns``.
ClickHouse has no traditional foreign keys; primary-key columns come from
MergeTree ``is_in_primary_key``.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from seal_core.database.config import clickhouse_default_port, parse_network_url
from seal_core.schema.models import (
    ColumnInfo,
    ColumnType,
    DatabaseSchema,
    TableKind,
    TableSchema,
)

_CLICKHOUSE_TYPE_MAP: dict[str, ColumnType] = {
    "int8": ColumnType.INTEGER,
    "int16": ColumnType.INTEGER,
    "int32": ColumnType.INTEGER,
    "int64": ColumnType.INTEGER,
    "int128": ColumnType.INTEGER,
    "int256": ColumnType.INTEGER,
    "uint8": ColumnType.INTEGER,
    "uint16": ColumnType.INTEGER,
    "uint32": ColumnType.INTEGER,
    "uint64": ColumnType.INTEGER,
    "uint128": ColumnType.INTEGER,
    "uint256": ColumnType.INTEGER,
    "float32": ColumnType.FLOAT,
    "float64": ColumnType.FLOAT,
    "bfloat16": ColumnType.FLOAT,
    "bool": ColumnType.BOOLEAN,
    "boolean": ColumnType.BOOLEAN,
    "string": ColumnType.STRING,
    "fixedstring": ColumnType.STRING,
    "uuid": ColumnType.STRING,
    "ipv4": ColumnType.STRING,
    "ipv6": ColumnType.STRING,
    "enum8": ColumnType.STRING,
    "enum16": ColumnType.STRING,
    "date": ColumnType.DATE,
    "date32": ColumnType.DATE,
    "datetime": ColumnType.TIMESTAMP,
    "datetime64": ColumnType.TIMESTAMP,
    "decimal": ColumnType.NUMERIC,
    "decimal32": ColumnType.NUMERIC,
    "decimal64": ColumnType.NUMERIC,
    "decimal128": ColumnType.NUMERIC,
    "decimal256": ColumnType.NUMERIC,
    "json": ColumnType.JSON,
    "object": ColumnType.JSON,
    "map": ColumnType.JSON,
    "tuple": ColumnType.JSON,
    "array": ColumnType.ARRAY,
}

_WRAPPER_RE = re.compile(
    r"^(?:Nullable|LowCardinality|SimpleAggregateFunction|AggregateFunction)\((.*)\)$",
    re.IGNORECASE,
)


def _unwrap_clickhouse_type(raw_type: str) -> str:
    """Strip Nullable() / LowCardinality() wrappers for type mapping."""
    current = raw_type.strip()
    while True:
        match = _WRAPPER_RE.match(current)
        if not match:
            break
        inner = match.group(1)
        # AggregateFunction(sum, Int64) → last arg is the value type.
        if "," in inner and current.lower().startswith("aggregatefunction"):
            inner = inner.rsplit(",", 1)[-1].strip()
        current = inner.strip()
    return current


def _normalize_clickhouse_type(raw_type: str) -> ColumnType:
    """Map a ClickHouse type string to ColumnType."""
    inner = _unwrap_clickhouse_type(raw_type)
    lower = inner.lower().strip()
    base = lower.split("(", 1)[0]
    if base in _CLICKHOUSE_TYPE_MAP:
        return _CLICKHOUSE_TYPE_MAP[base]
    if lower.startswith("array"):
        return ColumnType.ARRAY
    if lower.startswith("decimal"):
        return ColumnType.NUMERIC
    if lower.startswith("fixedstring") or lower.startswith("enum"):
        return ColumnType.STRING
    if lower.startswith("datetime"):
        return ColumnType.TIMESTAMP
    if lower.startswith("map") or lower.startswith("tuple") or lower.startswith("object"):
        return ColumnType.JSON
    return ColumnType.OTHER


_TABLES_QUERY = """
SELECT
    database,
    name,
    engine,
    total_rows,
    comment
FROM system.tables
WHERE database NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA')
  AND name NOT LIKE '.%'
ORDER BY database, name
"""

_COLUMNS_QUERY = """
SELECT
    database,
    table,
    name,
    type,
    position,
    default_kind,
    default_expression,
    comment,
    is_in_primary_key
FROM system.columns
WHERE database NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA')
  AND table NOT LIKE '.%'
ORDER BY database, table, position
"""


class ClickHouseIntrospector:
    """Schema introspector for ClickHouse.

    Uses clickhouse-connect (synchronous HTTP client). The async methods exist
    for SchemaIntrospector protocol compatibility.

    Usage:
        introspector = ClickHouseIntrospector("clickhouse://localhost:8123/default")
        schema = await introspector.introspect()
        await introspector.close()
    """

    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazily create and return a clickhouse-connect client."""
        if self._client is None:
            try:
                import clickhouse_connect
            except ImportError as exc:
                raise ImportError(
                    "ClickHouse support requires the clickhouse extra "
                    "(uv sync --extra clickhouse, or pip install 'seal-core[clickhouse]')."
                ) from exc

            params = parse_network_url(
                self._connection_string,
                default_port=clickhouse_default_port(self._connection_string),
                default_user="default",
                default_database="default",
            )
            self._client = clickhouse_connect.get_client(
                host=params.host,
                port=params.port,
                username=params.user,
                password=params.password,
                database=params.database or "default",
                secure=params.secure,
                autogenerate_session_id=False,
            )
        return self._client

    async def close(self) -> None:
        """Close the ClickHouse client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def _query(self, sql: str) -> list[dict[str, Any]]:
        """Run a system.* query and return list-of-dict rows."""
        client = self._get_client()
        result = client.query(sql)
        names = list(result.column_names)
        return [dict(zip(names, row, strict=False)) for row in result.result_rows]

    async def introspect(self) -> DatabaseSchema:
        """Introspect tables/views and columns from system catalogs."""
        tables_rows = await asyncio.to_thread(self._query, _TABLES_QUERY)
        columns_rows = await asyncio.to_thread(self._query, _COLUMNS_QUERY)

        columns_lookup: dict[str, list[ColumnInfo]] = {}
        for row in columns_rows:
            key = f"{row['database']}.{row['table']}"
            raw_type = str(row.get("type") or "")
            default_expr = row.get("default_expression")
            col = ColumnInfo(
                name=row["name"],
                data_type=raw_type,
                normalized_type=_normalize_clickhouse_type(raw_type),
                nullable="nullable" in raw_type.lower(),
                is_primary_key=bool(row.get("is_in_primary_key")),
                default_value=_optional_str(default_expr),
                description=_optional_str(row.get("comment")),
            )
            columns_lookup.setdefault(key, []).append(col)

        tables: list[TableSchema] = []
        for row in tables_rows:
            database = row["database"]
            name = row["name"]
            key = f"{database}.{name}"
            engine = str(row.get("engine") or "")
            kind = _table_kind_from_engine(engine)
            total_rows = row.get("total_rows")
            tables.append(
                TableSchema(
                    name=name,
                    schema_name=database,
                    kind=kind,
                    columns=columns_lookup.get(key, []),
                    row_count=int(total_rows) if total_rows is not None else None,
                    description=_optional_str(row.get("comment")),
                )
            )

        return DatabaseSchema(
            dialect="clickhouse",
            tables=tables,
            relationships=[],
            has_timescaledb=False,
        )


def _table_kind_from_engine(engine: str) -> TableKind:
    lower = engine.lower()
    if lower == "materializedview":
        return TableKind.MATERIALIZED_VIEW
    if lower in {"view", "liveview"}:
        return TableKind.VIEW
    return TableKind.TABLE


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
