"""Shared SQL safety rules for AST-based validation and sanitization."""

from __future__ import annotations

from enum import StrEnum

from sqlglot import exp

from seal_sql.limits import SanitizerLimits  # noqa: TC001 — used at runtime

# Root statement types allowed for analytics (read-only) queries.
ALLOWED_ROOT_TYPES: tuple[type[exp.Expression], ...] = (
    exp.Select,
    exp.Union,
    exp.Intersect,
    exp.Except,
)

READ_ONLY_REQUIRED_MSG = "Only read-only SELECT queries are allowed."


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
    COPY = "COPY"
    INTO = "INTO"
    COMMAND = "COMMAND"
    EXECUTE = "EXECUTE"
    PRAGMA = "PRAGMA"
    SET = "SET"
    ATTACH = "ATTACH"
    DETACH = "DETACH"
    TRANSACTION = "TRANSACTION"
    COMMIT = "COMMIT"
    ROLLBACK = "ROLLBACK"
    ANALYZE = "ANALYZE"
    REFRESH = "REFRESH"
    LOCK = "LOCK"


_BLOCKED_EXPRESSION_TYPES: dict[type[exp.Expression], BlockedOperation] = {
    exp.Drop: BlockedOperation.DROP,
    exp.Delete: BlockedOperation.DELETE,
    exp.Update: BlockedOperation.UPDATE,
    exp.Insert: BlockedOperation.INSERT,
    exp.Alter: BlockedOperation.ALTER,
    exp.Create: BlockedOperation.CREATE,
    exp.TruncateTable: BlockedOperation.TRUNCATE,
    exp.Grant: BlockedOperation.GRANT,
    exp.Revoke: BlockedOperation.REVOKE,
    exp.Merge: BlockedOperation.MERGE,
    exp.Copy: BlockedOperation.COPY,
    exp.Into: BlockedOperation.INTO,
    exp.Command: BlockedOperation.COMMAND,
    exp.Execute: BlockedOperation.EXECUTE,
    exp.Pragma: BlockedOperation.PRAGMA,
    exp.Set: BlockedOperation.SET,
    exp.Attach: BlockedOperation.ATTACH,
    exp.Detach: BlockedOperation.DETACH,
    exp.Transaction: BlockedOperation.TRANSACTION,
    exp.Commit: BlockedOperation.COMMIT,
    exp.Rollback: BlockedOperation.ROLLBACK,
    exp.Analyze: BlockedOperation.ANALYZE,
    exp.Refresh: BlockedOperation.REFRESH,
    exp.Lock: BlockedOperation.LOCK,
}


def find_blocked_operations(parsed: exp.Expression) -> list[str]:
    """Return human-readable messages for every blocked operation in the AST."""
    found: set[BlockedOperation] = set()

    for expr_type, op_name in _BLOCKED_EXPRESSION_TYPES.items():
        if isinstance(parsed, expr_type) or parsed.find(expr_type):
            found.add(op_name)

    return [
        f"Blocked operation: {op.value}. {READ_ONLY_REQUIRED_MSG}"
        for op in sorted(found, key=lambda o: o.value)
    ]


def is_allowed_root(parsed: exp.Expression) -> bool:
    """True when the top-level statement is a read-only select shape."""
    return isinstance(parsed, ALLOWED_ROOT_TYPES)


def root_type_name(parsed: exp.Expression) -> str:
    """Human-readable root expression type for error messages."""
    return type(parsed).__name__


def _integer_literal(expr: exp.Expression | None) -> int | None:
    """Parse an integer literal, including simple unary minus forms."""
    if expr is None:
        return None
    if isinstance(expr, exp.Literal) and expr.is_int:
        return int(expr.this)
    if isinstance(expr, exp.Neg):
        inner = expr.this
        if isinstance(inner, exp.Literal) and inner.is_int:
            return -int(inner.this)
    return None


def _validate_pagination_node(
    *,
    kind: str,
    node: exp.Limit | exp.Offset,
    max_allowed: int,
    dynamic_message: str,
) -> list[str]:
    """Validate one LIMIT or OFFSET node."""
    if node.expression is None:
        return [f"{kind} clause is missing a value."]

    val = _integer_literal(node.expression)
    if val is None:
        return [dynamic_message]
    if val < 0:
        return [f"{kind} {val} is not allowed. Use a non-negative integer."]
    if kind == "OFFSET" and val > max_allowed:
        return [
            f"OFFSET {val} exceeds the maximum of {max_allowed}. "
            f"Use a literal integer OFFSET up to {max_allowed}."
        ]
    return []


def validate_limit_and_offset_literals(
    parsed: exp.Expression,
    limits: SanitizerLimits,
) -> list[str]:
    """Return errors for invalid LIMIT/OFFSET clauses (dynamic, negative, over cap)."""
    errors: list[str] = []
    max_offset = limits.effective_max_offset

    for limit_node in parsed.find_all(exp.Limit):
        errors.extend(
            _validate_pagination_node(
                kind="LIMIT",
                node=limit_node,
                max_allowed=limits.max_rows,
                dynamic_message=(
                    "Dynamic LIMIT expressions are not allowed. "
                    f"Use a literal integer LIMIT up to {limits.max_rows}."
                ),
            )
        )

    for offset_node in parsed.find_all(exp.Offset):
        errors.extend(
            _validate_pagination_node(
                kind="OFFSET",
                node=offset_node,
                max_allowed=max_offset,
                dynamic_message=(
                    "Dynamic OFFSET expressions are not allowed. "
                    f"Use a literal integer OFFSET up to {max_offset}."
                ),
            )
        )

    return errors


def _clamp_limit_node(
    node: exp.Limit,
    *,
    max_rows: int,
    warnings: list[str],
) -> None:
    """Clamp a single LIMIT literal that exceeds max_rows (OFFSET is validate-only)."""
    val = _integer_literal(node.expression)
    if val is not None and val > max_rows:
        warnings.append(f"LIMIT {val} exceeds maximum of {max_rows}. Clamped to {max_rows}.")
        node.set("expression", exp.Literal.number(max_rows))


def enforce_limit_cap(
    parsed: exp.Expression,
    limits: SanitizerLimits,
    warnings: list[str],
) -> exp.Expression:
    """Clamp over-cap LIMIT literals and inject a root LIMIT when absent.

    OFFSET is validate-only (rejected in ``validate_limit_and_offset_literals``).
    """
    for limit_node in parsed.find_all(exp.Limit):
        _clamp_limit_node(limit_node, max_rows=limits.max_rows, warnings=warnings)

    if isinstance(parsed, ALLOWED_ROOT_TYPES) and parsed.args.get("limit") is None:
        warnings.append(f"No LIMIT clause found. Automatically added LIMIT {limits.max_rows}.")
        parsed = parsed.limit(limits.max_rows)

    return parsed


# Backwards-compatible alias.
clamp_limits_and_offsets = enforce_limit_cap


def count_joins(parsed: exp.Expression) -> int:
    """Count JOIN clauses in the query."""
    return len(list(parsed.find_all(exp.Join)))


def measure_subquery_depth(node: exp.Expression, depth: int = 0) -> int:
    """Recursively measure the maximum subquery nesting depth."""
    max_depth = depth

    for child in node.iter_expressions():
        if isinstance(child, exp.Subquery):
            child_depth = measure_subquery_depth(child, depth + 1)
            max_depth = max(max_depth, child_depth)
        else:
            child_depth = measure_subquery_depth(child, depth)
            max_depth = max(max_depth, child_depth)

    return max_depth


def check_complexity_bounds(parsed: exp.Expression, limits: SanitizerLimits) -> list[str]:
    """Return errors when JOIN or subquery depth exceeds configured limits."""
    errors: list[str] = []

    join_count = count_joins(parsed)
    if join_count > limits.max_joins:
        errors.append(f"Query has {join_count} JOINs, exceeding the maximum of {limits.max_joins}.")

    subquery_depth = measure_subquery_depth(parsed)
    if subquery_depth > limits.max_subquery_depth:
        errors.append(
            f"Query has subquery nesting depth of {subquery_depth}, "
            f"exceeding the maximum of {limits.max_subquery_depth}."
        )

    return errors


def run_safety_checks(
    parsed: exp.Expression,
    limits: SanitizerLimits,
) -> list[str]:
    """Run all blocking sanitizer checks that do not mutate the AST."""
    errors: list[str] = []
    errors.extend(find_blocked_operations(parsed))
    if not is_allowed_root(parsed):
        errors.append(f"Only SELECT queries are allowed. Got: {root_type_name(parsed)}")
    errors.extend(validate_limit_and_offset_literals(parsed, limits))
    errors.extend(check_complexity_bounds(parsed, limits))
    return errors
