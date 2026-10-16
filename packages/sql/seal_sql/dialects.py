"""Dialect mapping between internal identifiers and SQLGlot dialects.

Maps our DatabaseSchema.dialect strings (e.g., 'postgres', 'duckdb', 'mysql',
'sqlite', 'clickhouse') to the corresponding SQLGlot dialect objects. Also
provides transpilation support when the LLM generates SQL in a different dialect
than the target database.
"""

from __future__ import annotations

from enum import StrEnum

import sqlglot


class Dialect(StrEnum):
    """Supported database dialects."""

    POSTGRES = "postgres"
    DUCKDB = "duckdb"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    CLICKHOUSE = "clickhouse"


# Mapping from our internal dialect enum to SQLGlot dialect strings.
# SQLGlot uses its own naming conventions, so we keep this mapping explicit.
_DIALECT_MAP: dict[str, str] = {
    Dialect.POSTGRES: "postgres",
    Dialect.DUCKDB: "duckdb",
    Dialect.MYSQL: "mysql",
    "mariadb": "mysql",
    Dialect.SQLITE: "sqlite",
    Dialect.CLICKHOUSE: "clickhouse",
}


def to_sqlglot_dialect(dialect: str | Dialect) -> str:
    """Convert an internal dialect identifier to a SQLGlot dialect string.

    Args:
        dialect: Internal dialect string (e.g., 'postgres', 'mysql', 'clickhouse').

    Returns:
        The corresponding SQLGlot dialect string.

    Raises:
        ValueError: If the dialect is not supported.
    """
    key = dialect.value if isinstance(dialect, Dialect) else dialect.lower().strip()
    if key not in _DIALECT_MAP:
        raise ValueError(
            f"Unsupported dialect: '{dialect}'. "
            f"Supported dialects: {', '.join(_DIALECT_MAP.keys())}"
        )
    return _DIALECT_MAP[key]


def transpile(
    sql: str,
    *,
    source_dialect: str | Dialect,
    target_dialect: str | Dialect,
) -> str:
    """Transpile SQL from one dialect to another using SQLGlot.

    This is used when the LLM generates SQL in a different dialect than
    the target database. For example, the LLM might generate Postgres-style
    SQL but the user is targeting DuckDB.

    Args:
        sql: The SQL query to transpile.
        source_dialect: The dialect the SQL was written in.
        target_dialect: The dialect to transpile to.

    Returns:
        The transpiled SQL string.

    Raises:
        ValueError: If either dialect is unsupported.
        sqlglot.errors.ErrorLevel: If the SQL cannot be parsed.
    """
    source = to_sqlglot_dialect(source_dialect)
    target = to_sqlglot_dialect(target_dialect)

    if source == target:
        return sql

    results = sqlglot.transpile(sql, read=source, write=target)
    if not results:
        return sql
    return results[0]


def is_supported_dialect(dialect: str) -> bool:
    """Check whether a dialect string is supported.

    Args:
        dialect: Dialect string to check.

    Returns:
        True if the dialect is supported, False otherwise.
    """
    return dialect.lower().strip() in _DIALECT_MAP
