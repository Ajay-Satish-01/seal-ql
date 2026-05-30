"""Tests for the QueryExecutor module.

Tests cover:
1. DuckDB execution (unit tests — no external dependencies)
2. Timeout enforcement
3. Retry logic with exponential backoff
4. Row cap enforcement
5. Configuration validation
6. Error handling
7. Connection lifecycle

Postgres tests are NOT included here because they require a live database.
Those belong in integration tests (run via `make test-integration`).
"""

from __future__ import annotations

import asyncio
from typing import Any

import duckdb
import pytest
from seal_sql.executor import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_BASE_DELAY,
    DEFAULT_ROW_CAP,
    DEFAULT_TIMEOUT_SECONDS,
    ExecutionConfig,
    QueryExecutionError,
    QueryExecutor,
    QueryTimeoutError,
)
from seal_sql.result import QueryResult

# ---------------------------------------------------------------------------
# ExecutionConfig
# ---------------------------------------------------------------------------


class TestExecutionConfig:
    """Tests for ExecutionConfig defaults and customization."""

    def test_defaults(self) -> None:
        config = ExecutionConfig()
        assert config.timeout_seconds == DEFAULT_TIMEOUT_SECONDS
        assert config.max_retries == DEFAULT_MAX_RETRIES
        assert config.row_cap == DEFAULT_ROW_CAP
        assert config.retry_base_delay == DEFAULT_RETRY_BASE_DELAY

    def test_custom_config(self) -> None:
        config = ExecutionConfig(
            timeout_seconds=5.0,
            max_retries=1,
            row_cap=100,
            retry_base_delay=0.1,
        )
        assert config.timeout_seconds == 5.0
        assert config.max_retries == 1
        assert config.row_cap == 100
        assert config.retry_base_delay == 0.1

    def test_frozen(self) -> None:
        config = ExecutionConfig()
        with pytest.raises(AttributeError):
            config.timeout_seconds = 99.0  # type: ignore[misc]

    def test_default_constants(self) -> None:
        assert DEFAULT_TIMEOUT_SECONDS == 30.0
        assert DEFAULT_MAX_RETRIES == 2
        assert DEFAULT_ROW_CAP == 10_000
        assert DEFAULT_RETRY_BASE_DELAY == 0.5


# ---------------------------------------------------------------------------
# QueryExecutor initialization
# ---------------------------------------------------------------------------


class TestExecutorInit:
    """Tests for QueryExecutor initialization and validation."""

    def test_valid_postgres_dialect(self) -> None:
        executor = QueryExecutor(
            dialect="postgres", connection_string="postgresql://localhost/test"
        )
        assert executor._dialect == "postgres"

    def test_valid_duckdb_dialect(self) -> None:
        executor = QueryExecutor(dialect="duckdb", connection_string=":memory:")
        assert executor._dialect == "duckdb"

    def test_unsupported_dialect_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported dialect"):
            QueryExecutor(dialect="mysql", connection_string="mysql://localhost/test")

    def test_case_insensitive_dialect(self) -> None:
        executor = QueryExecutor(dialect="DUCKDB", connection_string=":memory:")
        assert executor._dialect == "duckdb"

    def test_custom_config(self) -> None:
        config = ExecutionConfig(timeout_seconds=10.0, max_retries=0)
        executor = QueryExecutor(dialect="duckdb", connection_string=":memory:", config=config)
        assert executor._config.timeout_seconds == 10.0
        assert executor._config.max_retries == 0


# ---------------------------------------------------------------------------
# DuckDB execution (real in-memory database)
# ---------------------------------------------------------------------------


class TestDuckDBExecution:
    """Integration-style tests using a real in-memory DuckDB database."""

    @pytest.fixture
    def executor(self) -> QueryExecutor:
        """Create a DuckDB executor with a seeded in-memory database."""
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE users (id INTEGER, name VARCHAR, score DOUBLE)")
        conn.execute("INSERT INTO users VALUES (1, 'Alice', 95.5)")
        conn.execute("INSERT INTO users VALUES (2, 'Bob', 87.3)")
        conn.execute("INSERT INTO users VALUES (3, 'Charlie', 92.1)")
        conn.close()

        # Note: DuckDB :memory: is per-connection, so we need a different approach.
        # We'll use the executor's own connection and seed it.
        executor = QueryExecutor(dialect="duckdb", connection_string=":memory:")
        # Seed the data through the executor's internal connection.
        _conn = executor._get_duckdb_conn()
        _conn.execute("CREATE TABLE users (id INTEGER, name VARCHAR, score DOUBLE)")
        _conn.execute("INSERT INTO users VALUES (1, 'Alice', 95.5)")
        _conn.execute("INSERT INTO users VALUES (2, 'Bob', 87.3)")
        _conn.execute("INSERT INTO users VALUES (3, 'Charlie', 92.1)")
        return executor

    @pytest.mark.asyncio
    async def test_simple_select(self, executor: QueryExecutor) -> None:
        result = await executor.execute("SELECT id, name FROM users ORDER BY id")
        assert isinstance(result, QueryResult)
        assert result.row_count == 3
        assert len(result.columns) == 2
        assert result.columns[0].name == "id"
        assert result.columns[1].name == "name"
        assert result.rows[0]["name"] == "Alice"
        assert result.rows[2]["name"] == "Charlie"

    @pytest.mark.asyncio
    async def test_select_with_where(self, executor: QueryExecutor) -> None:
        result = await executor.execute("SELECT name FROM users WHERE score > 90")
        assert result.row_count == 2
        names = {row["name"] for row in result.rows}
        assert names == {"Alice", "Charlie"}

    @pytest.mark.asyncio
    async def test_aggregate_query(self, executor: QueryExecutor) -> None:
        result = await executor.execute(
            "SELECT COUNT(*) as cnt, AVG(score) as avg_score FROM users"
        )
        assert result.row_count == 1
        assert result.rows[0]["cnt"] == 3
        assert round(result.rows[0]["avg_score"], 1) == 91.6

    @pytest.mark.asyncio
    async def test_empty_result(self, executor: QueryExecutor) -> None:
        result = await executor.execute("SELECT id FROM users WHERE id = 999")
        assert result.row_count == 0
        assert result.rows == []
        assert result.truncated is False

    @pytest.mark.asyncio
    async def test_execution_time_tracked(self, executor: QueryExecutor) -> None:
        result = await executor.execute("SELECT id FROM users")
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_sql_stored_in_result(self, executor: QueryExecutor) -> None:
        sql = "SELECT name FROM users ORDER BY name"
        result = await executor.execute(sql)
        assert result.sql == sql

    @pytest.mark.asyncio
    async def test_column_metadata(self, executor: QueryExecutor) -> None:
        result = await executor.execute("SELECT id, name, score FROM users LIMIT 1")
        assert len(result.columns) == 3
        col_names = [c.name for c in result.columns]
        assert col_names == ["id", "name", "score"]

    @pytest.mark.asyncio
    async def test_join_query(self, executor: QueryExecutor) -> None:
        conn = executor._get_duckdb_conn()
        conn.execute("CREATE TABLE orders (id INTEGER, user_id INTEGER, amount DOUBLE)")
        conn.execute("INSERT INTO orders VALUES (1, 1, 50.0)")
        conn.execute("INSERT INTO orders VALUES (2, 2, 75.0)")

        result = await executor.execute(
            "SELECT u.name, o.amount FROM users u JOIN orders o ON u.id = o.user_id ORDER BY u.name"
        )
        assert result.row_count == 2
        assert result.rows[0]["name"] == "Alice"
        assert result.rows[0]["amount"] == 50.0

    @pytest.mark.asyncio
    async def test_cte_query(self, executor: QueryExecutor) -> None:
        result = await executor.execute(
            "WITH high_scorers AS (SELECT name, score FROM users WHERE score > 90) "
            "SELECT name FROM high_scorers ORDER BY name"
        )
        assert result.row_count == 2

    @pytest.mark.asyncio
    async def test_close(self, executor: QueryExecutor) -> None:
        """Closing should release the connection."""
        await executor.execute("SELECT 1")
        assert executor._duckdb_conn is not None

        await executor.close()
        assert executor._duckdb_conn is None

    @pytest.mark.asyncio
    async def test_close_idempotent(self, executor: QueryExecutor) -> None:
        """Closing twice should not raise."""
        await executor.close()
        await executor.close()  # Should be a no-op.


# ---------------------------------------------------------------------------
# Row cap enforcement
# ---------------------------------------------------------------------------


class TestRowCap:
    """Tests for row cap enforcement as a safety net."""

    @pytest.fixture
    def executor(self) -> QueryExecutor:
        config = ExecutionConfig(row_cap=5)
        executor = QueryExecutor(dialect="duckdb", connection_string=":memory:", config=config)
        conn = executor._get_duckdb_conn()
        conn.execute("CREATE TABLE big_table (id INTEGER)")
        for i in range(20):
            conn.execute(f"INSERT INTO big_table VALUES ({i})")
        return executor

    @pytest.mark.asyncio
    async def test_truncates_when_exceeding_cap(self, executor: QueryExecutor) -> None:
        result = await executor.execute("SELECT id FROM big_table")
        assert result.row_count == 5
        assert result.truncated is True

    @pytest.mark.asyncio
    async def test_no_truncation_under_cap(self, executor: QueryExecutor) -> None:
        result = await executor.execute("SELECT id FROM big_table LIMIT 3")
        assert result.row_count == 3
        assert result.truncated is False


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


class TestRetryLogic:
    """Tests for retry with exponential backoff."""

    @pytest.mark.asyncio
    async def test_no_retry_on_success(self) -> None:
        """Successful execution should not trigger retries."""
        executor = QueryExecutor(
            dialect="duckdb",
            connection_string=":memory:",
            config=ExecutionConfig(max_retries=2),
        )
        conn = executor._get_duckdb_conn()
        conn.execute("CREATE TABLE t (id INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")

        result = await executor.execute("SELECT id FROM t")
        assert result.row_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure(self) -> None:
        """Transient failures should trigger retries."""
        executor = QueryExecutor(
            dialect="duckdb",
            connection_string=":memory:",
            config=ExecutionConfig(max_retries=2, retry_base_delay=0.01),
        )

        call_count = 0
        original_execute = executor._execute_once

        async def flaky_execute(sql: str, *, attempt: int = 1) -> QueryResult:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Transient error")
            # Seed data for the successful attempt.
            conn = executor._get_duckdb_conn()
            try:
                conn.execute("CREATE TABLE t (id INTEGER)")
                conn.execute("INSERT INTO t VALUES (1)")
            except Exception:
                pass
            return await original_execute(sql, attempt=attempt)

        executor._execute_once = flaky_execute  # type: ignore[assignment]

        result = await executor.execute("SELECT id FROM t")
        assert call_count == 3
        assert result.row_count == 1

    @pytest.mark.asyncio
    async def test_raises_after_all_retries_exhausted(self) -> None:
        """Should raise QueryExecutionError after all retries fail."""
        executor = QueryExecutor(
            dialect="duckdb",
            connection_string=":memory:",
            config=ExecutionConfig(max_retries=1, retry_base_delay=0.01),
        )

        async def always_fail(sql: str, *, attempt: int = 1) -> QueryResult:
            raise RuntimeError("Permanent error")

        executor._execute_once = always_fail  # type: ignore[assignment]

        with pytest.raises(QueryExecutionError) as exc_info:
            await executor.execute("SELECT 1")

        assert exc_info.value.attempts == 2  # 1 original + 1 retry
        assert "Permanent error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_no_retries_when_disabled(self) -> None:
        """With max_retries=0, should fail immediately."""
        executor = QueryExecutor(
            dialect="duckdb",
            connection_string=":memory:",
            config=ExecutionConfig(max_retries=0),
        )

        call_count = 0

        async def fail_once(sql: str, *, attempt: int = 1) -> QueryResult:
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Fail")

        executor._execute_once = fail_once  # type: ignore[assignment]

        with pytest.raises(QueryExecutionError):
            await executor.execute("SELECT 1")

        assert call_count == 1  # No retries.


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    """Tests for query timeout enforcement."""

    @pytest.mark.asyncio
    async def test_timeout_raises(self) -> None:
        """A slow query should raise QueryTimeoutError."""
        executor = QueryExecutor(
            dialect="duckdb",
            connection_string=":memory:",
            config=ExecutionConfig(timeout_seconds=0.1),
        )

        async def slow_execute(sql: str, *, attempt: int = 1) -> QueryResult:
            # Simulate a slow underlying execution that times out.
            raise TimeoutError()

        executor._execute_once = slow_execute  # type: ignore[assignment]

        # The execute method should catch the TimeoutError and re-raise as QueryTimeoutError
        # However, the timeout is raised inside _execute_once, so we need to test differently.
        # Let's test the real path: mock the DuckDB execution to be slow.

        async def really_slow(sql: str) -> Any:
            await asyncio.sleep(10)

        executor._execute_duckdb = really_slow  # type: ignore[assignment]

        with pytest.raises(QueryTimeoutError) as exc_info:
            await executor.execute("SELECT 1")

        assert exc_info.value.sql == "SELECT 1"

    @pytest.mark.asyncio
    async def test_no_retry_on_timeout(self) -> None:
        """Timeouts should not be retried — they'd likely time out again."""
        executor = QueryExecutor(
            dialect="duckdb",
            connection_string=":memory:",
            config=ExecutionConfig(timeout_seconds=0.05, max_retries=3),
        )

        call_count = 0

        async def slow_duckdb(sql: str) -> Any:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(10)  # Will always timeout
            return [], []

        executor._execute_duckdb = slow_duckdb  # type: ignore[assignment]

        with pytest.raises(QueryTimeoutError):
            await executor.execute("SELECT 1")

        assert call_count == 1  # Should NOT retry.


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------


class TestErrorTypes:
    """Tests for custom error classes."""

    def test_query_execution_error_attributes(self) -> None:
        err = QueryExecutionError(
            "Something broke",
            sql="SELECT 1",
            original_error=RuntimeError("db down"),
            attempts=3,
        )
        assert str(err) == "Something broke"
        assert err.sql == "SELECT 1"
        assert isinstance(err.original_error, RuntimeError)
        assert err.attempts == 3

    def test_query_timeout_error_is_execution_error(self) -> None:
        err = QueryTimeoutError("timed out", sql="SELECT 1")
        assert isinstance(err, QueryExecutionError)
        assert isinstance(err, Exception)

    def test_default_attributes(self) -> None:
        err = QueryExecutionError("fail")
        assert err.sql == ""
        assert err.original_error is None
        assert err.attempts == 1


# ---------------------------------------------------------------------------
# DuckDB execution — error cases
# ---------------------------------------------------------------------------


class TestDuckDBErrors:
    """Tests for DuckDB-specific error handling."""

    @pytest.mark.asyncio
    async def test_invalid_sql_raises(self) -> None:
        executor = QueryExecutor(
            dialect="duckdb",
            connection_string=":memory:",
            config=ExecutionConfig(max_retries=0),
        )
        conn = executor._get_duckdb_conn()
        conn.execute("CREATE TABLE t (id INTEGER)")

        with pytest.raises(QueryExecutionError):
            await executor.execute("INVALID SQL STATEMENT")

    @pytest.mark.asyncio
    async def test_table_not_found_raises(self) -> None:
        executor = QueryExecutor(
            dialect="duckdb",
            connection_string=":memory:",
            config=ExecutionConfig(max_retries=0),
        )

        with pytest.raises(QueryExecutionError):
            await executor.execute("SELECT * FROM nonexistent_table")


# ---------------------------------------------------------------------------
# Result integration
# ---------------------------------------------------------------------------


class TestResultIntegration:
    """Tests verifying QueryResult can be used for downstream conversions."""

    @pytest.fixture
    def executor(self) -> QueryExecutor:
        executor = QueryExecutor(dialect="duckdb", connection_string=":memory:")
        conn = executor._get_duckdb_conn()
        conn.execute("CREATE TABLE products (id INTEGER, name VARCHAR, price DOUBLE, created DATE)")
        conn.execute("INSERT INTO products VALUES (1, 'Widget', 9.99, '2025-01-15')")
        conn.execute("INSERT INTO products VALUES (2, 'Gadget', 24.50, '2025-02-20')")
        return executor

    @pytest.mark.asyncio
    async def test_result_to_json(self, executor: QueryExecutor) -> None:
        result = await executor.execute("SELECT id, name, price FROM products ORDER BY id")
        json_data = result.to_json()
        assert len(json_data) == 2
        assert json_data[0]["name"] == "Widget"
        assert json_data[1]["price"] == 24.5

    @pytest.mark.asyncio
    async def test_result_to_polars(self, executor: QueryExecutor) -> None:
        import polars as pl

        result = await executor.execute("SELECT id, name FROM products ORDER BY id")
        df = result.to_polars()
        assert isinstance(df, pl.DataFrame)
        assert df.shape == (2, 2)

    @pytest.mark.asyncio
    async def test_result_to_pandas(self, executor: QueryExecutor) -> None:
        pd = pytest.importorskip("pandas")

        result = await executor.execute("SELECT id, name FROM products ORDER BY id")
        df = result.to_pandas()
        assert isinstance(df, pd.DataFrame)
        assert df.shape == (2, 2)

    @pytest.mark.asyncio
    async def test_result_columns_match_query(self, executor: QueryExecutor) -> None:
        result = await executor.execute("SELECT name, price FROM products")
        col_names = [c.name for c in result.columns]
        assert col_names == ["name", "price"]
