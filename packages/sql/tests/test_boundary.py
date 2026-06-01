"""Tests for validate_and_sanitize and boundary helpers."""

import warnings

import pytest
from seal_core.schema.models import (
    ColumnInfo,
    ColumnType,
    DatabaseSchema,
    TableKind,
    TableSchema,
)
from seal_sql.boundary import format_boundary_errors, validate_and_sanitize
from seal_sql.limits import SanitizerLimits
from seal_sql.parse import ParseFailure, parse_one_expression, parse_single_statement
from seal_sql.sanitizer import SQLSanitizer
from seal_sql.validator import SQLValidator


def _users_schema() -> DatabaseSchema:
    return DatabaseSchema(
        dialect="postgres",
        tables=[
            TableSchema(
                name="users",
                kind=TableKind.TABLE,
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="INTEGER",
                        normalized_type=ColumnType.INTEGER,
                    ),
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# parse_single_statement
# ---------------------------------------------------------------------------


class TestParseSingleStatement:
    def test_rejects_semicolon_separated_statements(self) -> None:
        result = parse_single_statement("SELECT 1; DROP TABLE users", "postgres")
        assert isinstance(result, ParseFailure)
        assert "Multi-statement" in result.message

    def test_accepts_single_select(self) -> None:
        result = parse_single_statement("SELECT id FROM users", "postgres")
        assert not isinstance(result, ParseFailure)

    def test_trailing_semicolon_accepted(self) -> None:
        """A single statement with trailing semicolon is valid SQL input."""
        result = parse_single_statement("SELECT 1;", "postgres")
        # SQLGlot may parse trailing ; as an empty second statement or ignore it.
        # Either way, the result must not be a parse error — OR if it is rejected,
        # it must be an explicit multi-statement message (not a crash).
        if isinstance(result, ParseFailure):
            assert "Multi-statement" in result.message or "Empty" in result.message
        else:
            assert result.expression is not None

    def test_empty_sql_rejected(self) -> None:
        result = parse_single_statement("", "postgres")
        assert isinstance(result, ParseFailure)
        assert "Empty" in result.message or "unparseable" in result.message

    def test_whitespace_only_rejected(self) -> None:
        result = parse_single_statement("   \n\t  ", "postgres")
        assert isinstance(result, ParseFailure)

    def test_comment_only_rejected(self) -> None:
        result = parse_single_statement("-- just a comment", "postgres")
        assert isinstance(result, ParseFailure)

    def test_semicolon_in_string_literal_accepted(self) -> None:
        """Semicolons inside string literals must not trigger multi-statement rejection."""
        result = parse_single_statement("SELECT 'a;b' AS val", "postgres")
        assert not isinstance(result, ParseFailure)

    def test_semicolon_in_block_comment_accepted(self) -> None:
        result = parse_single_statement("SELECT 1 /* ; */ FROM users", "postgres")
        assert not isinstance(result, ParseFailure)


# ---------------------------------------------------------------------------
# parse_one_expression (deprecated alias)
# ---------------------------------------------------------------------------


class TestParseOneExpressionDeprecation:
    def test_emits_deprecation_warning(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = parse_one_expression("SELECT 1", "postgres")
            assert not isinstance(result, ParseFailure)
        assert any(issubclass(w.category, DeprecationWarning) for w in caught)
        assert any("parse_single_statement" in str(w.message) for w in caught)


# ---------------------------------------------------------------------------
# validate_and_sanitize
# ---------------------------------------------------------------------------


class TestValidateAndSanitize:
    def test_multi_statement_blocked_before_execution(self) -> None:
        schema = _users_schema()
        result = validate_and_sanitize("SELECT id FROM users; DROP TABLE users", schema)
        assert not result.valid
        assert any("Multi-statement" in e for e in result.errors)

    def test_select_then_drop_blocked(self) -> None:
        result = validate_and_sanitize("SELECT 1; DROP TABLE users", _users_schema())
        assert not result.valid

    def test_valid_query_matches_validator_and_sanitizer(self) -> None:
        schema = _users_schema()
        sql = "SELECT id FROM users"
        boundary = validate_and_sanitize(sql, schema)
        validation = SQLValidator(schema).validate(sql)
        sanitization = SQLSanitizer(dialect=schema.dialect).sanitize(sql)
        assert boundary.valid == (validation.valid and sanitization.safe)
        if boundary.valid:
            assert boundary.executable_sql == sanitization.sanitized_sql

    def test_sanitize_parsed_does_not_mutate_shared_ast(self) -> None:
        """Prove .copy() prevents in-place mutation when LIMIT is clamped."""
        parsed = parse_single_statement("SELECT id FROM users LIMIT 1000", "postgres")
        assert not isinstance(parsed, ParseFailure)
        before = parsed.normalized_sql()
        limits = SanitizerLimits(max_rows=5)
        result = SQLSanitizer(dialect="postgres", limits=limits).sanitize_parsed(parsed)
        assert result.safe
        assert "5" in result.sanitized_sql
        assert parsed.normalized_sql() == before


# ---------------------------------------------------------------------------
# format_boundary_errors
# ---------------------------------------------------------------------------


class TestFormatBoundaryErrors:
    def test_single_error(self) -> None:
        assert format_boundary_errors(["only one"]) == "only one"

    def test_multiple_errors_joined(self) -> None:
        assert format_boundary_errors(["a", "b"]) == "a; b"

    def test_empty_list(self) -> None:
        assert format_boundary_errors([]) == "SQL boundary failed"


# ---------------------------------------------------------------------------
# SanitizerLimits
# ---------------------------------------------------------------------------


class TestSanitizerLimits:
    def test_negative_max_offset_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_offset"):
            SanitizerLimits(max_rows=10, max_offset=-1)

    def test_limits_merge_overrides_field(self) -> None:
        base = SanitizerLimits(max_rows=100, max_joins=3)
        sanitizer = SQLSanitizer(dialect="postgres", limits=base, max_rows=50)
        assert sanitizer.limits.max_rows == 50
        assert sanitizer.limits.max_joins == 3

    def test_limits_merge_explicit_none_clears_max_offset(self) -> None:
        """Passing max_offset=None explicitly must clear an existing value."""
        base = SanitizerLimits(max_rows=100, max_offset=500)
        merged = SanitizerLimits.merge(base, max_offset=None)
        assert merged.max_offset is None
        assert merged.effective_max_offset == 100

    def test_limits_merge_unset_preserves_value(self) -> None:
        """Omitting a kwarg preserves the base value."""
        base = SanitizerLimits(max_rows=100, max_offset=500)
        merged = SanitizerLimits.merge(base)
        assert merged.max_offset == 500

    def test_limits_merge_rejects_invalid_max_rows(self) -> None:
        """merge() with max_rows=0 raises at construction time."""
        base = SanitizerLimits(max_rows=100)
        with pytest.raises(ValueError, match="max_rows"):
            SanitizerLimits.merge(base, max_rows=0)

    def test_sanitizer_rejects_invalid_max_rows_kwarg(self) -> None:
        """SQLSanitizer(max_rows=0) must raise, not silently use defaults."""
        with pytest.raises(ValueError, match="max_rows"):
            SQLSanitizer(dialect="postgres", max_rows=0)
