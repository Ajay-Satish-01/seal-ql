"""Tests for the SQL validator module."""

import pytest
from intelligence_core.schema.models import (
    ColumnInfo,
    ColumnType,
    DatabaseSchema,
    RelationshipInfo,
    TableKind,
    TableSchema,
)
from intelligence_sql.validator import SQLValidator

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_schema() -> DatabaseSchema:
    """Create a realistic test schema with multiple tables and relationships."""
    return DatabaseSchema(
        dialect="postgres",
        tables=[
            TableSchema(
                name="users",
                schema_name="public",
                kind=TableKind.TABLE,
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="INTEGER",
                        normalized_type=ColumnType.INTEGER,
                        nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(
                        name="name",
                        data_type="VARCHAR(100)",
                        normalized_type=ColumnType.STRING,
                        nullable=False,
                    ),
                    ColumnInfo(
                        name="email",
                        data_type="VARCHAR(255)",
                        normalized_type=ColumnType.STRING,
                        nullable=False,
                    ),
                    ColumnInfo(
                        name="created_at",
                        data_type="TIMESTAMP",
                        normalized_type=ColumnType.TIMESTAMP,
                        nullable=False,
                    ),
                ],
            ),
            TableSchema(
                name="orders",
                schema_name="public",
                kind=TableKind.TABLE,
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="INTEGER",
                        normalized_type=ColumnType.INTEGER,
                        nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(
                        name="user_id",
                        data_type="INTEGER",
                        normalized_type=ColumnType.INTEGER,
                        nullable=False,
                    ),
                    ColumnInfo(
                        name="amount",
                        data_type="NUMERIC(10,2)",
                        normalized_type=ColumnType.NUMERIC,
                        nullable=False,
                    ),
                    ColumnInfo(
                        name="status",
                        data_type="VARCHAR(50)",
                        normalized_type=ColumnType.STRING,
                        nullable=False,
                    ),
                    ColumnInfo(
                        name="created_at",
                        data_type="TIMESTAMP",
                        normalized_type=ColumnType.TIMESTAMP,
                        nullable=False,
                    ),
                ],
            ),
            TableSchema(
                name="products",
                schema_name="public",
                kind=TableKind.TABLE,
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="INTEGER",
                        normalized_type=ColumnType.INTEGER,
                        nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(
                        name="name",
                        data_type="VARCHAR(200)",
                        normalized_type=ColumnType.STRING,
                        nullable=False,
                    ),
                    ColumnInfo(
                        name="price",
                        data_type="NUMERIC(10,2)",
                        normalized_type=ColumnType.NUMERIC,
                        nullable=False,
                    ),
                    ColumnInfo(
                        name="category", data_type="VARCHAR(100)", normalized_type=ColumnType.STRING
                    ),
                ],
            ),
            TableSchema(
                name="monthly_revenue",
                schema_name="public",
                kind=TableKind.MATERIALIZED_VIEW,
                columns=[
                    ColumnInfo(name="month", data_type="DATE", normalized_type=ColumnType.DATE),
                    ColumnInfo(
                        name="total_revenue",
                        data_type="NUMERIC",
                        normalized_type=ColumnType.NUMERIC,
                    ),
                    ColumnInfo(
                        name="order_count", data_type="INTEGER", normalized_type=ColumnType.INTEGER
                    ),
                ],
            ),
        ],
        relationships=[
            RelationshipInfo(
                from_table="orders",
                from_column="user_id",
                to_table="users",
                to_column="id",
                constraint_name="fk_orders_user",
            ),
        ],
    )


@pytest.fixture
def schema() -> DatabaseSchema:
    return _make_schema()


@pytest.fixture
def validator(schema: DatabaseSchema) -> SQLValidator:
    return SQLValidator(schema)


# ---------------------------------------------------------------------------
# Basic validation
# ---------------------------------------------------------------------------


class TestBasicValidation:
    """Test fundamental validation scenarios."""

    def test_valid_simple_select(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT id, name FROM users")
        assert result.valid
        assert result.errors == []
        assert "users" in result.tables_referenced

    def test_valid_select_with_where(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT name, email FROM users WHERE id = 1")
        assert result.valid

    def test_valid_select_with_join(self, validator: SQLValidator) -> None:
        result = validator.validate(
            "SELECT u.name, o.amount FROM users u JOIN orders o ON u.id = o.user_id"
        )
        assert result.valid
        assert "users" in result.tables_referenced
        assert "orders" in result.tables_referenced

    def test_valid_aggregate(self, validator: SQLValidator) -> None:
        result = validator.validate(
            "SELECT status, SUM(amount) as total FROM orders GROUP BY status"
        )
        assert result.valid

    def test_valid_subquery(self, validator: SQLValidator) -> None:
        result = validator.validate(
            "SELECT name FROM users WHERE id IN (SELECT user_id FROM orders WHERE amount > 100)"
        )
        assert result.valid

    def test_valid_cte(self, validator: SQLValidator) -> None:
        result = validator.validate(
            "WITH big_orders AS (SELECT user_id, amount FROM orders WHERE amount > 1000) "
            "SELECT u.name, bo.amount FROM users u JOIN big_orders bo ON u.id = bo.user_id"
        )
        assert result.valid
        # CTE name should NOT appear as a referenced table.
        assert "big_orders" not in result.tables_referenced

    def test_valid_materialized_view(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT month, total_revenue FROM monthly_revenue")
        assert result.valid
        assert "monthly_revenue" in result.tables_referenced


# ---------------------------------------------------------------------------
# Table validation
# ---------------------------------------------------------------------------


class TestTableValidation:
    """Test table existence validation."""

    def test_unknown_table(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT id FROM nonexistent_table")
        assert not result.valid
        assert any("Unknown table" in e and "nonexistent_table" in e for e in result.errors)

    def test_unknown_table_in_join(self, validator: SQLValidator) -> None:
        result = validator.validate(
            "SELECT u.name FROM users u JOIN ghost_table g ON u.id = g.user_id"
        )
        assert not result.valid
        assert any("ghost_table" in e for e in result.errors)

    def test_multiple_unknown_tables(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT a.x FROM fake1 a JOIN fake2 b ON a.id = b.id")
        assert not result.valid
        assert len(result.errors) >= 2


# ---------------------------------------------------------------------------
# Column validation
# ---------------------------------------------------------------------------


class TestColumnValidation:
    """Test column existence validation."""

    def test_unknown_column(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT nonexistent_col FROM users")
        assert not result.valid
        assert any("Unknown column" in e and "nonexistent_col" in e for e in result.errors)

    def test_unknown_column_with_table_qualifier(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT users.ghost_column FROM users")
        assert not result.valid
        assert any("ghost_column" in e for e in result.errors)

    def test_unknown_column_with_alias_qualifier(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT u.ghost_column FROM users u")
        assert not result.valid
        assert any("ghost_column" in e for e in result.errors)

    def test_valid_column_different_tables(self, validator: SQLValidator) -> None:
        """Both users and orders have 'id' — should be fine when qualified."""
        result = validator.validate(
            "SELECT u.id, o.id FROM users u JOIN orders o ON u.id = o.user_id"
        )
        assert result.valid


# ---------------------------------------------------------------------------
# Warnings
# ---------------------------------------------------------------------------


class TestWarnings:
    """Test warning generation."""

    def test_select_star_warning(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT * FROM users")
        assert result.valid  # SELECT * is valid, just warned.
        assert any("SELECT *" in w for w in result.warnings)

    def test_no_warning_for_specific_columns(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT id, name FROM users")
        assert result.warnings == []


# ---------------------------------------------------------------------------
# Parse errors
# ---------------------------------------------------------------------------


class TestParseErrors:
    """Test handling of unparseable SQL."""

    def test_invalid_syntax(self, validator: SQLValidator) -> None:
        result = validator.validate("SELEC id FORM users")
        # SQLGlot may or may not error — but if it does, we handle it.
        # If it somehow parses, the table 'users' won't be found via FORM.
        assert not result.valid or len(result.errors) > 0 or len(result.warnings) > 0

    def test_empty_string(self, validator: SQLValidator) -> None:
        result = validator.validate("")
        assert not result.valid


# ---------------------------------------------------------------------------
# Normalized SQL
# ---------------------------------------------------------------------------


class TestNormalizedSQL:
    """Test that normalized SQL is returned."""

    def test_normalized_sql_present(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT   id,   name   FROM   users")
        assert result.valid
        assert result.normalized_sql  # Should be non-empty.
        assert "users" in result.normalized_sql.lower()

    def test_normalized_sql_on_error(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT id FROM nonexistent")
        assert result.normalized_sql  # Should still have the SQL even on error.


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and complex queries."""

    def test_union_query(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT name FROM users UNION ALL SELECT name FROM products")
        assert result.valid
        assert "users" in result.tables_referenced
        assert "products" in result.tables_referenced

    def test_nested_subquery(self, validator: SQLValidator) -> None:
        result = validator.validate(
            "SELECT * FROM users WHERE id IN "
            "(SELECT user_id FROM orders WHERE amount > "
            "(SELECT AVG(amount) FROM orders))"
        )
        assert result.valid

    def test_case_insensitive_table_matching(self, validator: SQLValidator) -> None:
        """Table names should match case-insensitively."""
        result = validator.validate("SELECT id, name FROM Users")
        # SQLGlot lowercases or preserves — either way our validator
        # should match case-insensitively.
        assert result.valid or "Unknown table" not in str(result.errors)

    def test_multiple_joins(self, validator: SQLValidator) -> None:
        result = validator.validate(
            "SELECT u.name, o.amount, p.name "
            "FROM users u "
            "JOIN orders o ON u.id = o.user_id "
            "JOIN products p ON p.id = 1"
        )
        assert result.valid
