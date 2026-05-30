"""SQL Sanitizer — security layer that blocks dangerous SQL and enforces limits.

Every SQL query from the LLM passes through here after validation. The sanitizer
ensures that only safe, read-only queries with bounded result sets reach the database.

All default values come from the centralized Settings class (via env vars).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import sqlglot
from seal_core.settings import get_settings
from sqlglot import exp
from sqlglot.errors import ParseError

from seal_sql.dialects import to_sqlglot_dialect


def _default_max_rows() -> int:
    return get_settings().max_rows


def _default_max_joins() -> int:
    return get_settings().max_joins


def _default_max_subquery_depth() -> int:
    return get_settings().max_subquery_depth


# Backwards-compatible aliases for code that imports these directly.
# These are evaluated at import time but match the env-configurable defaults.
DEFAULT_MAX_ROWS = 10_000
DEFAULT_MAX_JOINS = 10
DEFAULT_MAX_SUBQUERY_DEPTH = 5


class BlockedOperation(StrEnum):
    """SQL operations that are unconditionally blocked."""

    DROP = "DROP"
    DELETE = "DELETE"
    UPDATE = "UPDATE"
    INSERT = "INSERT"
    ALTER = "ALTER"
    CREATE = "CREATE"
    TRUNCATE = "TRUNCATE"
    GRANT = "GRANT"
    REVOKE = "REVOKE"
    MERGE = "MERGE"


# Map SQLGlot expression types to our blocked operation names.
_BLOCKED_EXPRESSION_TYPES: dict[type[exp.Expression], BlockedOperation] = {
    exp.Drop: BlockedOperation.DROP,
    exp.Delete: BlockedOperation.DELETE,
    exp.Update: BlockedOperation.UPDATE,
    exp.Insert: BlockedOperation.INSERT,
    exp.Alter: BlockedOperation.ALTER,
    exp.Create: BlockedOperation.CREATE,
    exp.Grant: BlockedOperation.GRANT,
}


@dataclass(frozen=True)
class SanitizationResult:
    """Result of SQL sanitization.

    Attributes:
        safe: Whether the SQL is safe to execute.
        sanitized_sql: The (potentially rewritten) SQL string.
        warnings: Non-blocking issues (e.g., LIMIT was injected).
        blocked_operations: Operations that caused the query to be blocked.
    """

    safe: bool
    sanitized_sql: str = ""
    warnings: list[str] = field(default_factory=list)
    blocked_operations: list[str] = field(default_factory=list)


class SQLSanitizer:
    """Sanitizes SQL queries for safe execution.

    Performs the following:
    1. Blocks destructive operations (DROP, DELETE, UPDATE, INSERT, ALTER, etc.)
    2. Blocks multi-statement queries (SQL injection prevention)
    3. Enforces a LIMIT clause (injects one if missing)
    4. Enforces query complexity bounds (max joins, max subquery depth)

    When no explicit limits are provided, values are read from the centralized
    Settings class (env vars: MAX_ROWS, MAX_JOINS, MAX_SUBQUERY_DEPTH).

    Example:
        >>> sanitizer = SQLSanitizer(dialect="postgres", max_rows=1000)
        >>> result = sanitizer.sanitize("SELECT * FROM users")
        >>> assert result.safe
        >>> assert "LIMIT" in result.sanitized_sql
    """

    def __init__(
        self,
        dialect: str = "postgres",
        *,
        max_rows: int | None = None,
        max_joins: int | None = None,
        max_subquery_depth: int | None = None,
    ) -> None:
        """Initialize the sanitizer.

        Args:
            dialect: Database dialect string.
            max_rows: Maximum number of rows allowed. Falls back to Settings.max_rows.
            max_joins: Maximum number of JOIN clauses allowed. Falls back to Settings.max_joins.
            max_subquery_depth: Maximum nesting depth of subqueries.
                Falls back to Settings.max_subquery_depth.
        """
        self._dialect = to_sqlglot_dialect(dialect)
        self._max_rows = max_rows if max_rows is not None else _default_max_rows()
        self._max_joins = max_joins if max_joins is not None else _default_max_joins()
        self._max_subquery_depth = (
            max_subquery_depth if max_subquery_depth is not None else _default_max_subquery_depth()
        )

    def sanitize(self, sql: str) -> SanitizationResult:
        """Sanitize a SQL query for safe execution.

        Args:
            sql: The SQL query string to sanitize.

        Returns:
            A SanitizationResult with the outcome.
        """
        warnings: list[str] = []
        blocked_ops: list[str] = []

        # --- Step 1: Block multi-statement queries ---
        try:
            statements = sqlglot.parse(sql, dialect=self._dialect)
        except ParseError as e:
            return SanitizationResult(
                safe=False,
                sanitized_sql=sql,
                blocked_operations=[f"Parse error: {e}"],
            )

        if len(statements) > 1:
            return SanitizationResult(
                safe=False,
                sanitized_sql=sql,
                blocked_operations=[
                    "Multi-statement queries are not allowed. "
                    "Only a single SELECT statement is permitted."
                ],
            )

        if not statements or statements[0] is None:
            return SanitizationResult(
                safe=False,
                sanitized_sql=sql,
                blocked_operations=["Empty or unparseable SQL."],
            )

        parsed = statements[0]

        # --- Step 2: Block destructive operations ---
        for expr_type, op_name in _BLOCKED_EXPRESSION_TYPES.items():
            if isinstance(parsed, expr_type) or parsed.find(expr_type):
                blocked_ops.append(
                    f"Blocked operation: {op_name.value}. "
                    "Only read-only SELECT queries are allowed."
                )

        # Check for TRUNCATE, REVOKE, MERGE via the raw text approach
        # since SQLGlot may not have dedicated expression types for all of these.
        sql_upper = sql.upper().strip()
        for op in (BlockedOperation.TRUNCATE, BlockedOperation.REVOKE, BlockedOperation.MERGE):
            if sql_upper.startswith(op.value):
                blocked_ops.append(
                    f"Blocked operation: {op.value}. Only read-only SELECT queries are allowed."
                )

        if blocked_ops:
            return SanitizationResult(
                safe=False,
                sanitized_sql=sql,
                blocked_operations=blocked_ops,
            )

        # --- Step 3: Verify it's a SELECT ---
        if not isinstance(parsed, exp.Select):
            # Could be a UNION, CTE, etc. — walk to find the core select.
            has_select = parsed.find(exp.Select) is not None
            if not has_select:
                return SanitizationResult(
                    safe=False,
                    sanitized_sql=sql,
                    blocked_operations=[
                        f"Only SELECT queries are allowed. Got: {type(parsed).__name__}"
                    ],
                )

        # --- Step 4: Enforce complexity bounds ---
        join_count = len(list(parsed.find_all(exp.Join)))
        if join_count > self._max_joins:
            return SanitizationResult(
                safe=False,
                sanitized_sql=sql,
                blocked_operations=[
                    f"Query has {join_count} JOINs, exceeding the maximum of {self._max_joins}."
                ],
            )

        subquery_depth = self._measure_subquery_depth(parsed)
        if subquery_depth > self._max_subquery_depth:
            return SanitizationResult(
                safe=False,
                sanitized_sql=sql,
                blocked_operations=[
                    f"Query has subquery nesting depth of {subquery_depth}, "
                    f"exceeding the maximum of {self._max_subquery_depth}."
                ],
            )

        # --- Step 5: Enforce LIMIT ---
        parsed = self._enforce_limit(parsed, warnings)

        sanitized_sql = parsed.sql(dialect=self._dialect, pretty=False)

        return SanitizationResult(
            safe=True,
            sanitized_sql=sanitized_sql,
            warnings=warnings,
        )

    def _enforce_limit(self, parsed: exp.Expression, warnings: list[str]) -> exp.Expression:
        """Ensure the query has a LIMIT clause, injecting one if missing.

        If an existing LIMIT exceeds max_rows, it's clamped down.

        Args:
            parsed: The parsed expression.
            warnings: List to append warnings to.

        Returns:
            The (potentially modified) expression.
        """
        # Find the outermost SELECT or UNION.
        target = parsed

        existing_limit = target.find(exp.Limit)
        if existing_limit:
            # Check if the existing limit is higher than our max.
            limit_expr = existing_limit.expression
            if isinstance(limit_expr, exp.Literal) and limit_expr.is_int:
                limit_val = int(limit_expr.this)
                if limit_val > self._max_rows:
                    warnings.append(
                        f"LIMIT {limit_val} exceeds maximum of {self._max_rows}. "
                        f"Clamped to {self._max_rows}."
                    )
                    existing_limit.set("expression", exp.Literal.number(self._max_rows))
        else:
            # No LIMIT found — inject one.
            warnings.append(f"No LIMIT clause found. Automatically added LIMIT {self._max_rows}.")
            # For a top-level SELECT, set the limit directly.
            if isinstance(target, exp.Select):
                target = target.limit(self._max_rows)
            else:
                # For UNION or other compound, wrap in a subquery with LIMIT.
                # Actually, SQLGlot's .limit() works on unions too.
                target = target.limit(self._max_rows)

        return target

    def _measure_subquery_depth(self, node: exp.Expression, depth: int = 0) -> int:
        """Recursively measure the maximum subquery nesting depth.

        Args:
            node: The expression tree node.
            depth: Current depth counter.

        Returns:
            The maximum subquery depth found.
        """
        max_depth = depth

        for child in node.iter_expressions():
            if isinstance(child, exp.Subquery):
                child_depth = self._measure_subquery_depth(child, depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._measure_subquery_depth(child, depth)
                max_depth = max(max_depth, child_depth)

        return max_depth
