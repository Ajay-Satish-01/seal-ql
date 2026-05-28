"""QueryExecutor — safe, sandboxed SQL query execution.

Executes validated and sanitized SQL queries against Postgres (via asyncpg)
or DuckDB databases. Provides:
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

from intelligence_sql.dialects import Dialect, to_sqlglot_dialect
from intelligence_sql.result import ColumnMetadata, QueryResult

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
        from intelligence_core.settings import get_settings

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
    """Executes SQL queries safely against Postgres or DuckDB.

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
            dialect: Database dialect ('postgres' or 'duckdb').
            connection_string: Database connection string.
            config: Optional execution configuration. Uses defaults if not provided.
        """
        # Validate dialect early.
        to_sqlglot_dialect(dialect)

        self._dialect = dialect.lower().strip()
        self._connection_string = connection_string
        self._config = config or ExecutionConfig()

        # Lazily initialized connections.
        self._pg_pool: Any = None  # asyncpg.Pool
        self._duckdb_conn: Any = None  # duckdb.DuckDBPyConnection

    async def close(self) -> None:
        """Close the underlying database connection / pool."""
        if self._pg_pool is not None:
            await self._pg_pool.close()
            self._pg_pool = None

        if self._duckdb_conn is not None:
            self._duckdb_conn.close()
            self._duckdb_conn = None

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
