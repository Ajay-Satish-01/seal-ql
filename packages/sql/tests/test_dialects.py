"""Tests for the dialect mapping module."""

import pytest
from intelligence_sql.dialects import (
    Dialect,
    is_supported_dialect,
    to_sqlglot_dialect,
    transpile,
)


class TestDialectEnum:
    """Tests for the Dialect enum."""

    def test_postgres_value(self) -> None:
        assert Dialect.POSTGRES == "postgres"

    def test_duckdb_value(self) -> None:
        assert Dialect.DUCKDB == "duckdb"

    def test_enum_from_string(self) -> None:
        assert Dialect("postgres") == Dialect.POSTGRES
        assert Dialect("duckdb") == Dialect.DUCKDB


class TestToSqlglotDialect:
    """Tests for to_sqlglot_dialect()."""

    def test_postgres_string(self) -> None:
        assert to_sqlglot_dialect("postgres") == "postgres"

    def test_duckdb_string(self) -> None:
        assert to_sqlglot_dialect("duckdb") == "duckdb"

    def test_enum_value(self) -> None:
        assert to_sqlglot_dialect(Dialect.POSTGRES) == "postgres"
        assert to_sqlglot_dialect(Dialect.DUCKDB) == "duckdb"

    def test_case_insensitive(self) -> None:
        assert to_sqlglot_dialect("POSTGRES") == "postgres"
        assert to_sqlglot_dialect("DuckDB") == "duckdb"

    def test_strips_whitespace(self) -> None:
        assert to_sqlglot_dialect("  postgres  ") == "postgres"

    def test_unsupported_dialect_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported dialect"):
            to_sqlglot_dialect("mysql")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported dialect"):
            to_sqlglot_dialect("")


class TestIsSupportedDialect:
    """Tests for is_supported_dialect()."""

    def test_supported(self) -> None:
        assert is_supported_dialect("postgres") is True
        assert is_supported_dialect("duckdb") is True

    def test_unsupported(self) -> None:
        assert is_supported_dialect("mysql") is False
        assert is_supported_dialect("sqlite") is False

    def test_case_insensitive(self) -> None:
        assert is_supported_dialect("POSTGRES") is True
        assert is_supported_dialect("DuckDB") is True


class TestTranspile:
    """Tests for cross-dialect transpilation."""

    def test_same_dialect_noop(self) -> None:
        sql = "SELECT id, name FROM users WHERE id = 1"
        result = transpile(sql, source_dialect="postgres", target_dialect="postgres")
        assert result == sql

    def test_postgres_to_duckdb(self) -> None:
        # Postgres uses :: for casting, DuckDB uses CAST()
        sql = "SELECT created_at::DATE FROM events"
        result = transpile(sql, source_dialect="postgres", target_dialect="duckdb")
        assert "CAST" in result.upper()

    def test_enum_values_work(self) -> None:
        sql = "SELECT 1"
        result = transpile(sql, source_dialect=Dialect.POSTGRES, target_dialect=Dialect.DUCKDB)
        assert "1" in result

    def test_unsupported_source_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported dialect"):
            transpile("SELECT 1", source_dialect="mysql", target_dialect="postgres")

    def test_unsupported_target_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported dialect"):
            transpile("SELECT 1", source_dialect="postgres", target_dialect="mysql")
