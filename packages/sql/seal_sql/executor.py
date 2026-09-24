"""QueryExecutor — safe, sandboxed SQL query execution.

Executes validated and sanitized SQL queries against Postgres (asyncpg),
DuckDB, MySQL/MariaDB (aiomysql), SQLite (aiosqlite), or ClickHouse
(clickhouse-connect in a thread pool). Provides:
  - Configurable query timeout (default 30s)
  - Automatic retry with exponential backoff (default 2 retries)
  - Row cap enforcement as a safety net
  - Normalized QueryResult output

Usage:
    executor = QueryExecutor(dialect="postgres", connection_string="postgresql://...")
    result = await executor.execute("SELECT id, name FROM users LIMIT 100")
    await executor.close()
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from seal_sql.dialects import Dialect, to_sqlglot_dialect
from seal_sql.result import ColumnMetadata, QueryResult

logger = logging.getLogger(__name__)


# ============================================================
# Error types
# ============================================================


class QueryExecutionError(Exception):
    """Raised when query execution fails after all retries.

    Attributes:
        sql: The SQL that failed.
        original_error: The underlying database error.
        attempts: How many attempts were made.
    """

    def __init__(
        self,
        message: str,
        *,
        sql: str = "",
        original_error: Exception | None = None,
        attempts: int = 1,
    ) -> None:
        super().__init__(message)
        self.sql = sql
        self.original_error = original_error
        self.attempts = attempts


class QueryTimeoutError(QueryExecutionError):
    """Raised when a query exceeds the configured timeout."""


# ============================================================
# Configuration
# ============================================================

# Backwards-compatible aliases (import-time values matching the env defaults).
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_ROW_CAP = 10_000
DEFAULT_RETRY_BASE_DELAY = 0.5  # seconds


@dataclass(frozen=True)
class ExecutionConfig:
    """Configuration for the query executor.

    Attributes:
        timeout_seconds: Maximum seconds to wait for query completion.
        max_retries: Number of retry attempts after the first failure.
        row_cap: Maximum number of rows to return (safety net).
        retry_base_delay: Base delay in seconds for exponential backoff.
    """

    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    row_cap: int = DEFAULT_ROW_CAP
    retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY

    @classmethod
    def from_settings(cls) -> ExecutionConfig:
        """Create an ExecutionConfig populated from the centralized Settings.

        Reads ``QUERY_TIMEOUT_SECONDS``, ``QUERY_MAX_RETRIES``,
        ``QUERY_ROW_CAP``, and ``QUERY_RETRY_BASE_DELAY`` from environment
        variables via the Settings class.

        Returns:
            An ExecutionConfig instance with env-backed values.
        """
        from seal_core.settings import get_settings

        settings = get_settings()
        return cls(
            timeout_seconds=settings.query_timeout_seconds,
            max_retries=settings.query_max_retries,
            row_cap=settings.query_row_cap,
            retry_base_delay=settings.query_retry_base_delay,
        )


# ============================================================
# Executor
# ============================================================


class QueryExecutor:
    """Executes SQL queries safely against a supported dialect.

    Handles connection management, timeouts, retries, and result normalization.
    Each execution returns a QueryResult with metadata.

    Example:
        >>> executor = QueryExecutor(dialect="postgres", connection_string="postgresql://...")
        >>> result = await executor.execute("SELECT id, name FROM users LIMIT 10")
        >>> print(result.row_count)
        10
        >>> df = result.to_polars()
    """

    def __init__(
        self,
        dialect: str,
        connection_string: str,
        config: ExecutionConfig | None = None,
    ) -> None:
        """Initialize the executor.

        Args:
            dialect: Database dialect (postgres, duckdb, mysql, sqlite, clickhouse).
            connection_string: Database connection string or file path.
            config: Optional execution configuration. Uses defaults if not provided.
        """
        # Validate dialect early. MariaDB shares the MySQL SQLGlot dialect.
        key = dialect.lower().strip()
        if key == "mariadb":
            key = Dialect.MYSQL
        to_sqlglot_dialect(key)

        self._dialect = key
        self._connection_string = connection_string
        self._config = config or ExecutionConfig()

        # Lazily initialized connections.
        self._pg_pool: Any = None  # asyncpg.Pool
        self._duckdb_conn: Any = None  # duckdb.DuckDBPyConnection
        self._mysql_pool: Any = None  # aiomysql.Pool
        self._sqlite_conn: Any = None  # aiosqlite.Connection
        self._clickhouse_client: Any = None  # clickhouse_connect.driver.Client

    async def close(self) -> None:
        """Close the underlying database connection / pool."""
        if self._pg_pool is not None:
            await self._pg_pool.close()
            self._pg_pool = None

        if self._duckdb_conn is not None:
            self._duckdb_conn.close()
            self._duckdb_conn = None

        if self._mysql_pool is not None:
            self._mysql_pool.close()
            await self._mysql_pool.wait_closed()
            self._mysql_pool = None

        if self._sqlite_conn is not None:
            await self._sqlite_conn.close()
            self._sqlite_conn = None

        if self._clickhouse_client is not None:
            self._clickhouse_client.close()
            self._clickhouse_client = None

    async def execute(self, sql: str) -> QueryResult:
        """Execute a SQL query with timeout, retry, and row cap.

        Args:
            sql: The (validated + sanitized) SQL query to execute.

        Returns:
            A QueryResult with rows, metadata, and timing information.

        Raises:
            QueryTimeoutError: If the query exceeds the configured timeout.
            QueryExecutionError: If the query fails after all retries.
        """
        last_error: Exception | None = None
        total_attempts = 1 + self._config.max_retries

        for attempt in range(1, total_attempts + 1):
            try:
                return await self._execute_once(sql, attempt=attempt)
            except TimeoutError as exc:
                logger.warning(
                    "Query timed out (attempt %d/%d, timeout=%.1fs): %s",
                    attempt,
                    total_attempts,
                    self._config.timeout_seconds,
                    sql[:200],
                )
                last_error = exc
                # Timeouts are not retried — they'd likely just time out again.
                raise QueryTimeoutError(
                    f"Query timed out after {self._config.timeout_seconds}s",
                    sql=sql,
                    original_error=exc,
                    attempts=attempt,
                ) from exc
            except Exception as exc:
                logger.warning(
                    "Query execution failed (attempt %d/%d): %s — %s",
                    attempt,
                    total_attempts,
                    type(exc).__name__,
                    str(exc)[:300],
                )
                last_error = exc

                if attempt < total_attempts:
                    delay = self._config.retry_base_delay * (2 ** (attempt - 1))
                    logger.info("Retrying in %.1fs...", delay)
                    await asyncio.sleep(delay)

        raise QueryExecutionError(
            f"Query failed after {total_attempts} attempts: {last_error}",
            sql=sql,
            original_error=last_error,
            attempts=total_attempts,
        )

    async def _execute_once(self, sql: str, *, attempt: int = 1) -> QueryResult:
        """Execute the query once (no retry), with timeout and row cap.

        Args:
            sql: SQL query to execute.
            attempt: Which attempt number (for logging).

        Returns:
            QueryResult from the database.
        """
        start = time.perf_counter()

        if self._dialect == Dialect.POSTGRES:
            raw_rows, columns = await asyncio.wait_for(
                self._execute_postgres(sql),
                timeout=self._config.timeout_seconds,
            )
        elif self._dialect == Dialect.DUCKDB:
            raw_rows, columns = await asyncio.wait_for(
                self._execute_duckdb(sql),
                timeout=self._config.timeout_seconds,
            )
        elif self._dialect == Dialect.MYSQL:
            raw_rows, columns = await asyncio.wait_for(
                self._execute_mysql(sql),
                timeout=self._config.timeout_seconds,
            )
        elif self._dialect == Dialect.SQLITE:
            raw_rows, columns = await asyncio.wait_for(
                self._execute_sqlite(sql),
                timeout=self._config.timeout_seconds,
            )
        elif self._dialect == Dialect.CLICKHOUSE:
            raw_rows, columns = await asyncio.wait_for(
                self._execute_clickhouse(sql),
                timeout=self._config.timeout_seconds,
            )
        else:
            raise QueryExecutionError(
                f"Unsupported dialect for execution: {self._dialect}",
                sql=sql,
                attempts=attempt,
            )

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Enforce row cap as a safety net.
        truncated = len(raw_rows) > self._config.row_cap
        if truncated:
            raw_rows = raw_rows[: self._config.row_cap]
            logger.info("Result truncated to %d rows (row cap)", self._config.row_cap)

        return QueryResult(
            columns=columns,
            rows=raw_rows,
            row_count=len(raw_rows),
            execution_time_ms=round(elapsed_ms, 2),
            truncated=truncated,
            sql=sql,
        )

    # ============================================================
    # Postgres execution
    # ============================================================

    async def _get_pg_pool(self) -> Any:
        """Lazily create and return the asyncpg connection pool."""
        if self._pg_pool is None:
            import asyncpg

            conn_str = self._connection_string.replace("postgresql+asyncpg://", "postgresql://")
            self._pg_pool = await asyncpg.create_pool(conn_str, min_size=1, max_size=5)
        return self._pg_pool

    async def _execute_postgres(
        self, sql: str
    ) -> tuple[list[dict[str, Any]], list[ColumnMetadata]]:
        """Execute SQL against Postgres via asyncpg.

        Returns:
            Tuple of (rows as list of dicts, column metadata).
        """
        pool = await self._get_pg_pool()

        async with pool.acquire() as conn:
            # Use a prepared statement for type info.
            stmt = await conn.prepare(sql)

            # Extract column metadata from the prepared statement.
            attributes = stmt.get_attributes()
            columns = [
                ColumnMetadata(
                    name=attr.name,
                    type=_pg_oid_to_type_name(attr.type.oid)
                    if hasattr(attr.type, "oid")
                    else "str",
                    nullable=True,
                )
                for attr in attributes
            ]

            # Fetch all rows.
            records = await stmt.fetch()

            # Convert asyncpg Records to dicts.
            rows = [dict(record) for record in records]

        return rows, columns

    # ============================================================
    # DuckDB execution
    # ============================================================

    def _get_duckdb_conn(self) -> Any:
        """Lazily create and return the DuckDB connection."""
        if self._duckdb_conn is None:
            import duckdb

            self._duckdb_conn = duckdb.connect(self._connection_string)
        return self._duckdb_conn

    async def _execute_duckdb(self, sql: str) -> tuple[list[dict[str, Any]], list[ColumnMetadata]]:
        """Execute SQL against DuckDB.

        DuckDB is synchronous/in-process, so we run it in a thread pool
        to avoid blocking the async event loop.

        Returns:
            Tuple of (rows as list of dicts, column metadata).
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_duckdb_sync, sql)

    def _execute_duckdb_sync(self, sql: str) -> tuple[list[dict[str, Any]], list[ColumnMetadata]]:
        """Synchronous DuckDB execution.

        Returns:
            Tuple of (rows as list of dicts, column metadata).
        """
        conn = self._get_duckdb_conn()
        result = conn.execute(sql)

        # Column descriptions: list of (name, type, ...)
        description = result.description or []
        columns = [
            ColumnMetadata(
                name=col[0],
                type=col[1] if len(col) > 1 else "str",
                nullable=True,
            )
            for col in description
        ]

        # Fetch all rows.
        raw_rows = result.fetchall()
        col_names = [col.name for col in columns]

        rows = [dict(zip(col_names, row, strict=False)) for row in raw_rows]

        return rows, columns

    # ============================================================
    # MySQL / MariaDB execution
    # ============================================================

    async def _get_mysql_pool(self) -> Any:
        """Lazily create and return the aiomysql connection pool."""
        if self._mysql_pool is None:
            try:
                import aiomysql
            except ImportError as exc:
                raise ImportError(
                    "MySQL/MariaDB support requires the mysql extra "
                    "(uv sync --extra mysql, or pip install 'seal-sql[mysql]')."
                ) from exc
            from seal_core.database.config import parse_network_url

            params = parse_network_url(
                self._connection_string,
                default_port=3306,
                default_user="root",
            )
            self._mysql_pool = await aiomysql.create_pool(
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
        return self._mysql_pool

    async def _execute_mysql(self, sql: str) -> tuple[list[dict[str, Any]], list[ColumnMetadata]]:
        """Execute SQL against MySQL/MariaDB via aiomysql."""
        try:
            import aiomysql
        except ImportError as exc:
            raise ImportError(
                "MySQL/MariaDB support requires the mysql extra "
                "(uv sync --extra mysql, or pip install 'seal-sql[mysql]')."
            ) from exc

        pool = await self._get_mysql_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql)
                records = await cur.fetchall()
                description = cur.description or []

        columns = [
            ColumnMetadata(
                name=col[0],
                type=_mysql_type_code_name(col[1]) if len(col) > 1 else "str",
                nullable=True if len(col) < 7 else bool(col[6]),
            )
            for col in description
        ]
        rows = [dict(record) for record in records]
        return rows, columns

    # ============================================================
    # SQLite execution
    # ============================================================

    async def _get_sqlite_conn(self) -> Any:
        """Lazily create and return the aiosqlite connection."""
        if self._sqlite_conn is None:
            try:
                import aiosqlite
            except ImportError as exc:
                raise ImportError(
                    "SQLite support requires the sqlite extra "
                    "(uv sync --extra sqlite, or pip install 'seal-sql[sqlite]')."
                ) from exc

            self._sqlite_conn = await aiosqlite.connect(self._connection_string)
            self._sqlite_conn.row_factory = aiosqlite.Row
        return self._sqlite_conn

    async def _execute_sqlite(self, sql: str) -> tuple[list[dict[str, Any]], list[ColumnMetadata]]:
        """Execute SQL against SQLite via aiosqlite."""
        conn = await self._get_sqlite_conn()
        cursor = await conn.execute(sql)
        raw_rows = await cursor.fetchall()
        description = cursor.description or []
        await cursor.close()

        columns = [
            ColumnMetadata(name=col[0], type="str", nullable=True) for col in description
        ]
        rows = [dict(row) for row in raw_rows]
        return rows, columns

    # ============================================================
    # ClickHouse execution
    # ============================================================

    def _get_clickhouse_client(self) -> Any:
        """Lazily create and return a clickhouse-connect client."""
        if self._clickhouse_client is None:
            try:
                import clickhouse_connect
            except ImportError as exc:
                raise ImportError(
                    "ClickHouse support requires the clickhouse extra "
                    "(uv sync --extra clickhouse, or pip install 'seal-sql[clickhouse]')."
                ) from exc
            from seal_core.database.config import clickhouse_default_port, parse_network_url

            params = parse_network_url(
                self._connection_string,
                default_port=clickhouse_default_port(self._connection_string),
                default_user="default",
                default_database="default",
            )
            self._clickhouse_client = clickhouse_connect.get_client(
                host=params.host,
                port=params.port,
                username=params.user,
                password=params.password,
                database=params.database or "default",
                secure=params.secure,
            )
        return self._clickhouse_client

    async def _execute_clickhouse(
        self, sql: str
    ) -> tuple[list[dict[str, Any]], list[ColumnMetadata]]:
        """Execute SQL against ClickHouse.

        clickhouse-connect is synchronous, so work runs in a thread pool.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_clickhouse_sync, sql)

    def _execute_clickhouse_sync(
        self, sql: str
    ) -> tuple[list[dict[str, Any]], list[ColumnMetadata]]:
        """Synchronous ClickHouse execution via clickhouse-connect."""
        client = self._get_clickhouse_client()
        timeout = max(1, int(self._config.timeout_seconds))
        result = client.query(sql, settings={"max_execution_time": timeout})
        names = list(result.column_names)
        type_names = [str(t) for t in result.column_types]
        columns = [
            ColumnMetadata(name=name, type=type_name or "str", nullable=True)
            for name, type_name in zip(names, type_names, strict=False)
        ]
        rows = [dict(zip(names, row, strict=False)) for row in result.result_rows]
        return rows, columns


# ============================================================
# Helpers
# ============================================================

# Common Postgres type OIDs → human-readable names.
# See: https://www.postgresql.org/docs/current/datatype-oid.html
_PG_OID_MAP: dict[int, str] = {
    16: "bool",
    20: "int8",
    21: "int2",
    23: "int4",
    25: "text",
    700: "float4",
    701: "float8",
    1043: "varchar",
    1082: "date",
    1114: "timestamp",
    1184: "timestamptz",
    1700: "numeric",
    2950: "uuid",
    3802: "jsonb",
    114: "json",
}


def _pg_oid_to_type_name(oid: int) -> str:
    """Convert a Postgres type OID to a human-readable type name."""
    return _PG_OID_MAP.get(oid, f"oid:{oid}")


# pymysql / MySQLdb FIELD_TYPE codes used by aiomysql descriptions.
_MYSQL_FIELD_TYPE_MAP: dict[int, str] = {
    0: "decimal",
    1: "tinyint",
    2: "smallint",
    3: "int",
    4: "float",
    5: "double",
    7: "timestamp",
    8: "bigint",
    9: "mediumint",
    10: "date",
    11: "time",
    12: "datetime",
    13: "year",
    15: "varchar",
    16: "bit",
    245: "json",
    246: "decimal",
    247: "enum",
    248: "set",
    249: "tinyblob",
    250: "mediumblob",
    251: "longblob",
    252: "blob",
    253: "varchar",
    254: "char",
}


def _mysql_type_code_name(type_code: object) -> str:
    """Convert a MySQL field type code to a readable name."""
    if isinstance(type_code, int):
        return _MYSQL_FIELD_TYPE_MAP.get(type_code, f"mysql:{type_code}")
    return str(type_code) if type_code else "str"
