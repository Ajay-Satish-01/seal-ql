"""Tests for shared SQL safety rules."""

import sqlglot
from seal_sql.limits import SanitizerLimits
from seal_sql.safety import (
    enforce_limit_cap,
    find_blocked_operations,
    is_allowed_root,
    run_safety_checks,
    validate_limit_and_offset_literals,
)


class TestFindBlockedOperations:
    def test_select_into_blocked(self) -> None:
        parsed = sqlglot.parse_one("SELECT * INTO t FROM users", dialect="postgres")
        blocked = find_blocked_operations(parsed)
        assert any("INTO" in msg for msg in blocked)

    def test_lock_blocked(self) -> None:
        parsed = sqlglot.parse_one("SELECT * FROM users FOR UPDATE", dialect="postgres")
        blocked = find_blocked_operations(parsed)
        assert any("LOCK" in msg for msg in blocked)


class TestIsAllowedRoot:
    def test_command_not_allowed(self) -> None:
        parsed = sqlglot.parse_one("EXPLAIN SELECT 1", dialect="postgres")
        assert not is_allowed_root(parsed)


class TestLimitValidation:
    def test_negative_limit_rejected(self) -> None:
        parsed = sqlglot.parse_one("SELECT 1 LIMIT -1", dialect="postgres")
        limits = SanitizerLimits(max_rows=100, max_joins=10, max_subquery_depth=5)
        errors = validate_limit_and_offset_literals(parsed, limits)
        assert any("LIMIT -1" in e for e in errors)
        assert not any("Dynamic LIMIT" in e for e in errors)

    def test_dynamic_limit_rejected(self) -> None:
        parsed = sqlglot.parse_one("SELECT 1 LIMIT (SELECT 10)", dialect="postgres")
        limits = SanitizerLimits(max_rows=100, max_joins=10, max_subquery_depth=5)
        errors = validate_limit_and_offset_literals(parsed, limits)
        assert any("Dynamic LIMIT" in e for e in errors)

    def test_offset_over_cap_rejected(self) -> None:
        parsed = sqlglot.parse_one("SELECT 1 LIMIT 10 OFFSET 500", dialect="postgres")
        limits = SanitizerLimits(max_rows=100, max_joins=10, max_subquery_depth=5)
        errors = validate_limit_and_offset_literals(parsed, limits)
        assert any("OFFSET 500 exceeds" in e for e in errors)


class TestEnforceLimitCap:
    def test_clamps_inner_limit(self) -> None:
        parsed = sqlglot.parse_one(
            "SELECT * FROM (SELECT id FROM users LIMIT 999999) AS u", dialect="postgres"
        )
        limits = SanitizerLimits(max_rows=100, max_joins=10, max_subquery_depth=5)
        warnings: list[str] = []
        clamped = enforce_limit_cap(parsed, limits, warnings)
        assert "LIMIT 100" in clamped.sql(dialect="postgres")
        assert any("Clamped" in w for w in warnings)

    def test_injects_root_limit_with_offset_only(self) -> None:
        parsed = sqlglot.parse_one("SELECT id FROM users OFFSET 10", dialect="postgres")
        limits = SanitizerLimits(max_rows=50, max_joins=10, max_subquery_depth=5)
        warnings: list[str] = []
        clamped = enforce_limit_cap(parsed, limits, warnings)
        out = clamped.sql(dialect="postgres")
        assert "LIMIT 50" in out.upper()


class TestRunSafetyChecks:
    def test_for_update_blocked(self) -> None:
        parsed = sqlglot.parse_one("SELECT * FROM users FOR UPDATE", dialect="postgres")
        limits = SanitizerLimits(max_rows=100, max_joins=10, max_subquery_depth=5)
        assert run_safety_checks(parsed, limits)
