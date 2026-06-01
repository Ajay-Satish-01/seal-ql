"""SQL Sanitizer — security layer that blocks dangerous SQL and enforces limits."""

from __future__ import annotations

from dataclasses import dataclass, field

from seal_sql.dialects import to_sqlglot_dialect
from seal_sql.limits import UNSET, SanitizerLimits, _Unset
from seal_sql.parse import ParsedStatement, ParseFailure, parse_single_statement
from seal_sql.safety import enforce_limit_cap, run_safety_checks


@dataclass(frozen=True)
class SanitizationResult:
    """Result of SQL sanitization."""

    safe: bool
    sanitized_sql: str = ""
    warnings: list[str] = field(default_factory=list)
    blocked_operations: list[str] = field(default_factory=list)


class SQLSanitizer:
    """Sanitizes SQL queries for safe execution (AST-based zero-trust boundary)."""

    def __init__(
        self,
        dialect: str = "postgres",
        *,
        max_rows: int | _Unset = UNSET,
        max_joins: int | _Unset = UNSET,
        max_subquery_depth: int | _Unset = UNSET,
        max_offset: int | None | _Unset = UNSET,
        limits: SanitizerLimits | None = None,
    ) -> None:
        """Initialize the sanitizer.

        When ``limits`` is provided it is the base; per-field kwargs override it.
        Omitted kwargs (``UNSET``) keep the base value; explicit values override.
        With no ``limits``, env-backed defaults serve as the base.
        """
        base = limits if limits is not None else SanitizerLimits.from_settings()
        self._limits = SanitizerLimits.merge(
            base,
            max_rows=max_rows,
            max_joins=max_joins,
            max_subquery_depth=max_subquery_depth,
            max_offset=max_offset,
        )
        self._dialect = to_sqlglot_dialect(dialect)

    @property
    def limits(self) -> SanitizerLimits:
        return self._limits

    def sanitize(self, sql: str) -> SanitizationResult:
        """Sanitize a SQL query string for safe execution."""
        parsed = parse_single_statement(sql, self._dialect)
        if isinstance(parsed, ParseFailure):
            return SanitizationResult(
                safe=False,
                sanitized_sql=parsed.source_sql,
                blocked_operations=[parsed.message],
            )
        return self.sanitize_parsed(parsed)

    def sanitize_parsed(self, parsed: ParsedStatement) -> SanitizationResult:
        """Sanitize an already-parsed statement (avoids a second parse)."""
        warnings: list[str] = []
        blocked = run_safety_checks(parsed.expression, self._limits)
        if blocked:
            return SanitizationResult(
                safe=False,
                sanitized_sql=parsed.normalized_sql(),
                blocked_operations=blocked,
            )

        # Copy before mutating so callers holding ``parsed`` see the pre-sanitize AST.
        expression = parsed.expression.copy()
        expression = enforce_limit_cap(expression, self._limits, warnings)
        return SanitizationResult(
            safe=True,
            sanitized_sql=expression.sql(dialect=parsed.dialect, pretty=False),
            warnings=warnings,
        )
