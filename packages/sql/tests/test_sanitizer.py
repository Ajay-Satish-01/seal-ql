"""Tests for the SQL sanitizer module."""

import pytest
from seal_sql.limits import DEFAULT_MAX_JOINS, DEFAULT_MAX_ROWS, DEFAULT_MAX_SUBQUERY_DEPTH
from seal_sql.sanitizer import SQLSanitizer


@pytest.fixture
def sanitizer() -> SQLSanitizer:
    """Default Postgres sanitizer."""
    return SQLSanitizer(dialect="postgres")


@pytest.fixture
def strict_sanitizer() -> SQLSanitizer:
    """Sanitizer with tight limits for testing bounds enforcement."""
    return SQLSanitizer(
        dialect="postgres",
        max_rows=100,
        max_joins=2,
        max_subquery_depth=2,
    )


# ---------------------------------------------------------------------------
# Safe queries
# ---------------------------------------------------------------------------


class TestSafeQueries:
    """Test that legitimate SELECT queries pass."""

    def test_simple_select(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("SELECT id, name FROM users LIMIT 10")
        assert result.safe
        assert result.sanitized_sql

    def test_select_with_join(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize(
            "SELECT u.name, o.amount FROM users u JOIN orders o ON u.id = o.user_id LIMIT 100"
        )
        assert result.safe

    def test_select_with_aggregation(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("SELECT status, COUNT(*) FROM orders GROUP BY status LIMIT 50")
        assert result.safe

    def test_select_with_subquery(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize(
            "SELECT name FROM users WHERE id IN (SELECT user_id FROM orders) LIMIT 100"
        )
        assert result.safe

    def test_cte_query(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize(
            "WITH top_users AS (SELECT user_id, SUM(amount) as total FROM orders "
            "GROUP BY user_id) SELECT * FROM top_users LIMIT 10"
        )
        assert result.safe

    def test_union_query(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize(
            "SELECT name FROM users UNION ALL SELECT name FROM products LIMIT 100"
        )
        assert result.safe


# ---------------------------------------------------------------------------
# Blocked destructive operations
# ---------------------------------------------------------------------------


class TestBlockedOperations:
    """Test that destructive SQL is always blocked."""

    def test_drop_table(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("DROP TABLE users")
        assert not result.safe
        assert any("DROP" in op for op in result.blocked_operations)

    def test_delete(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("DELETE FROM users WHERE id = 1")
        assert not result.safe
        assert any("DELETE" in op for op in result.blocked_operations)

    def test_update(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("UPDATE users SET name = 'hacked' WHERE id = 1")
        assert not result.safe
        assert any("UPDATE" in op for op in result.blocked_operations)

    def test_insert(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("INSERT INTO users (name) VALUES ('evil')")
        assert not result.safe
        assert any("INSERT" in op for op in result.blocked_operations)

    def test_alter_table(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("ALTER TABLE users ADD COLUMN hacked BOOLEAN")
        assert not result.safe
        assert any("ALTER" in op for op in result.blocked_operations)

    def test_create_table(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("CREATE TABLE evil (id INT)")
        assert not result.safe
        assert any("CREATE" in op for op in result.blocked_operations)

    def test_truncate(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("TRUNCATE TABLE users")
        assert not result.safe
        assert any("TRUNCATE" in op for op in result.blocked_operations)

    def test_grant(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("GRANT ALL ON users TO evil_user")
        assert not result.safe

    def test_revoke(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("REVOKE ALL ON users FROM good_user")
        assert not result.safe

    def test_merge(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize(
            "MERGE INTO users u USING orders o ON u.id = o.user_id "
            "WHEN MATCHED THEN UPDATE SET name = 'x'"
        )
        assert not result.safe
        assert any("MERGE" in op for op in result.blocked_operations)

    def test_select_into(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("SELECT * INTO new_users FROM users")
        assert not result.safe
        assert any("INTO" in op for op in result.blocked_operations)

    def test_copy(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("COPY users TO STDOUT")
        assert not result.safe
        assert any("COPY" in op for op in result.blocked_operations)

    def test_execute(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("EXECUTE my_proc()")
        assert not result.safe

    def test_pragma(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("PRAGMA table_info(users)")
        assert not result.safe

    def test_set(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("SET search_path = public")
        assert not result.safe

    def test_for_update(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("SELECT * FROM users FOR UPDATE")
        assert not result.safe
        assert any("LOCK" in op for op in result.blocked_operations)

    def test_for_share(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("SELECT * FROM users FOR SHARE")
        assert not result.safe

    def test_dynamic_limit(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("SELECT id FROM users LIMIT (SELECT 1000)")
        assert not result.safe
        assert any("Dynamic LIMIT" in op for op in result.blocked_operations)

    def test_negative_limit(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("SELECT id FROM users LIMIT -1")
        assert not result.safe
        assert any("LIMIT -1" in op for op in result.blocked_operations)

    def test_excessive_offset_rejected(self, strict_sanitizer: SQLSanitizer) -> None:
        result = strict_sanitizer.sanitize("SELECT id FROM users LIMIT 10 OFFSET 500")
        assert not result.safe
        assert any("OFFSET" in op for op in result.blocked_operations)

    def test_inner_limit_clamped(self, strict_sanitizer: SQLSanitizer) -> None:
        result = strict_sanitizer.sanitize("SELECT * FROM (SELECT id FROM users LIMIT 999) AS u")
        assert result.safe
        assert "100" in result.sanitized_sql

    def test_nested_delete_in_select(self, sanitizer: SQLSanitizer) -> None:
        """Destructive ops nested anywhere in the AST must be blocked."""
        result = sanitizer.sanitize(
            "SELECT * FROM users WHERE id IN (SELECT user_id FROM deleted_orders)"
        )
        assert result.safe
        result = sanitizer.sanitize(
            "WITH d AS (DELETE FROM orders RETURNING user_id) SELECT * FROM users"
        )
        assert not result.safe
        assert any("DELETE" in op for op in result.blocked_operations)


# ---------------------------------------------------------------------------
# Multi-statement blocking
# ---------------------------------------------------------------------------


class TestMultiStatement:
    """Test that multi-statement queries are blocked."""

    def test_two_selects(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("SELECT 1; SELECT 2")
        assert not result.safe
        assert any("Multi-statement" in op for op in result.blocked_operations)

    def test_select_then_drop(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("SELECT 1; DROP TABLE users")
        assert not result.safe

    def test_empty_sql(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("")
        assert not result.safe


# ---------------------------------------------------------------------------
# LIMIT enforcement
# ---------------------------------------------------------------------------


class TestLimitEnforcement:
    """Test LIMIT injection and clamping."""

    def test_inject_limit_when_missing(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("SELECT id FROM users")
        assert result.safe
        assert "LIMIT" in result.sanitized_sql.upper()
        assert any("No LIMIT" in w for w in result.warnings)

    def test_inject_outer_limit_when_subquery_has_limit(self, sanitizer: SQLSanitizer) -> None:
        sql = "SELECT * FROM (SELECT id FROM users LIMIT 5) AS u"
        result = sanitizer.sanitize(sql)
        assert result.safe
        assert result.sanitized_sql.upper().count("LIMIT") >= 2

    def test_preserve_existing_limit(self, sanitizer: SQLSanitizer) -> None:
        result = sanitizer.sanitize("SELECT id FROM users LIMIT 50")
        assert result.safe
        assert "50" in result.sanitized_sql
        assert result.warnings == []  # No clamping needed.

    def test_clamp_excessive_limit(self, strict_sanitizer: SQLSanitizer) -> None:
        """When LIMIT exceeds max_rows, it should be clamped down."""
        result = strict_sanitizer.sanitize("SELECT id FROM users LIMIT 999999")
        assert result.safe
        assert any("Clamped" in w or "exceeds" in w for w in result.warnings)
        # The sanitized SQL should have the clamped value.
        assert "100" in result.sanitized_sql

    def test_limit_at_boundary(self, strict_sanitizer: SQLSanitizer) -> None:
        """LIMIT exactly at max_rows should be fine."""
        result = strict_sanitizer.sanitize("SELECT id FROM users LIMIT 100")
        assert result.safe
        assert result.warnings == []

    def test_default_max_rows(self) -> None:
        """Default max rows is 10,000."""
        assert DEFAULT_MAX_ROWS == 10_000


# ---------------------------------------------------------------------------
# Complexity bounds
# ---------------------------------------------------------------------------


class TestComplexityBounds:
    """Test query complexity enforcement."""

    def test_too_many_joins(self, strict_sanitizer: SQLSanitizer) -> None:
        """Strict sanitizer allows max 2 joins."""
        sql = (
            "SELECT * FROM a "
            "JOIN b ON a.id = b.id "
            "JOIN c ON b.id = c.id "
            "JOIN d ON c.id = d.id "
            "LIMIT 10"
        )
        result = strict_sanitizer.sanitize(sql)
        assert not result.safe
        assert any("JOIN" in op for op in result.blocked_operations)

    def test_joins_at_limit(self, strict_sanitizer: SQLSanitizer) -> None:
        """Exactly 2 joins should be allowed."""
        sql = "SELECT * FROM a JOIN b ON a.id = b.id JOIN c ON b.id = c.id LIMIT 10"
        result = strict_sanitizer.sanitize(sql)
        assert result.safe

    def test_deeply_nested_subqueries(self, strict_sanitizer: SQLSanitizer) -> None:
        """Strict sanitizer allows max depth 2."""
        sql = (
            "SELECT * FROM users WHERE id IN "
            "(SELECT user_id FROM orders WHERE amount > "
            "(SELECT AVG(amount) FROM orders WHERE status IN "
            "(SELECT status FROM order_statuses))) "
            "LIMIT 10"
        )
        result = strict_sanitizer.sanitize(sql)
        assert not result.safe
        assert any("subquery" in op.lower() for op in result.blocked_operations)

    def test_default_complexity_limits(self) -> None:
        assert DEFAULT_MAX_JOINS == 10
        assert DEFAULT_MAX_SUBQUERY_DEPTH == 5


# ---------------------------------------------------------------------------
# DuckDB dialect
# ---------------------------------------------------------------------------


class TestDuckDBDialect:
    """Test sanitizer with DuckDB dialect."""

    def test_duckdb_select(self) -> None:
        sanitizer = SQLSanitizer(dialect="duckdb")
        result = sanitizer.sanitize("SELECT * FROM users LIMIT 10")
        assert result.safe

    def test_duckdb_blocks_drop(self) -> None:
        sanitizer = SQLSanitizer(dialect="duckdb")
        result = sanitizer.sanitize("DROP TABLE users")
        assert not result.safe


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class TestConfiguration:
    """Test sanitizer configuration options."""

    def test_custom_max_rows(self) -> None:
        sanitizer = SQLSanitizer(dialect="postgres", max_rows=500)
        result = sanitizer.sanitize("SELECT id FROM users")
        assert result.safe
        assert "500" in result.sanitized_sql

    def test_unsupported_dialect_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported dialect"):
            SQLSanitizer(dialect="mysql")
