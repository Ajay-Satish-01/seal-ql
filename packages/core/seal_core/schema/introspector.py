"""Schema introspector protocol and factory.

All database-specific introspectors implement the SchemaIntrospector protocol.
The get_introspector() factory selects the right implementation based on the dialect.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from seal_core.schema.models import DatabaseSchema


@runtime_checkable
class SchemaIntrospector(Protocol):
    """Protocol that all schema introspectors must implement.

    Each introspector connects to a specific database type and extracts
    the full schema (tables, columns, relationships) into our canonical models.
    """

    async def introspect(self) -> DatabaseSchema:
        """Introspect the database and return the full schema.

        Returns:
            DatabaseSchema with all tables, columns, and relationships populated.
        """
        ...

    async def close(self) -> None:
        """Close the database connection / cleanup resources."""
        ...


def get_introspector(dialect: str, connection_string: str) -> SchemaIntrospector:
    """Factory to create the appropriate introspector for a given database dialect.

    Args:
        dialect: Database dialect — postgres, duckdb, mysql, sqlite, or clickhouse.
        connection_string: Connection string or path for the database.

    Returns:
        An instance of the appropriate SchemaIntrospector.

    Raises:
        ValueError: If the dialect is not supported.
    """
    key = dialect.lower().strip()
    if key == "duckdb":
        from seal_core.schema.duckdb import DuckDBIntrospector

        return DuckDBIntrospector(connection_string)
    if key in {"postgres", "postgresql"}:
        from seal_core.schema.postgres import PostgresIntrospector

        return PostgresIntrospector(connection_string)
    if key in {"mysql", "mariadb"}:
        from seal_core.schema.mysql import MySQLIntrospector

        return MySQLIntrospector(connection_string)
    if key == "sqlite":
        from seal_core.schema.sqlite import SQLiteIntrospector

        return SQLiteIntrospector(connection_string)
    if key == "clickhouse":
        from seal_core.schema.clickhouse import ClickHouseIntrospector

        return ClickHouseIntrospector(connection_string)
    raise ValueError(
        f"Unsupported dialect: '{dialect}'. "
        "Supported dialects: 'postgres', 'duckdb', 'mysql', 'sqlite', 'clickhouse'."
    )
