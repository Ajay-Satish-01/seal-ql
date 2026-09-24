"""Optional live-database integration tests.

Skipped unless the corresponding environment variable is set:

- ``SEAL_TEST_MYSQL_URL`` — MySQL or MariaDB (pytest marker ``mysql``)
- ``SEAL_TEST_CLICKHOUSE_URL`` — ClickHouse (pytest marker ``clickhouse``)

These are not run in default CI. Example:

    SEAL_TEST_MYSQL_URL='mysql://root:pass@127.0.0.1:3306/seal_test' \\
      uv run pytest -m mysql packages/sql/tests/test_live_dialects.py
"""

from __future__ import annotations

import importlib.util
import os

import pytest
from seal_sql.executor import ExecutionConfig, QueryExecutor

_MYSQL_URL = os.environ.get("SEAL_TEST_MYSQL_URL", "").strip()
_CLICKHOUSE_URL = os.environ.get("SEAL_TEST_CLICKHOUSE_URL", "").strip()


@pytest.mark.mysql
@pytest.mark.skipif(not _MYSQL_URL, reason="SEAL_TEST_MYSQL_URL is not set")
@pytest.mark.skipif(
    importlib.util.find_spec("aiomysql") is None,
    reason="mysql extra (aiomysql) is not installed",
)
@pytest.mark.asyncio
async def test_mysql_live_select() -> None:
    executor = QueryExecutor(
        dialect="mysql",
        connection_string=_MYSQL_URL,
        config=ExecutionConfig(max_retries=0),
    )
    try:
        result = await executor.execute("SELECT 1 AS n")
        assert result.row_count == 1
        assert result.rows[0]["n"] == 1
    finally:
        await executor.close()


@pytest.mark.clickhouse
@pytest.mark.skipif(not _CLICKHOUSE_URL, reason="SEAL_TEST_CLICKHOUSE_URL is not set")
@pytest.mark.skipif(
    importlib.util.find_spec("clickhouse_connect") is None,
    reason="clickhouse extra (clickhouse-connect) is not installed",
)
@pytest.mark.asyncio
async def test_clickhouse_live_select() -> None:
    executor = QueryExecutor(
        dialect="clickhouse",
        connection_string=_CLICKHOUSE_URL,
        config=ExecutionConfig(max_retries=0),
    )
    try:
        result = await executor.execute("SELECT 1 AS n")
        assert result.row_count == 1
        assert int(result.rows[0]["n"]) == 1
    finally:
        await executor.close()
