"""Seal SQL — validation, sanitization, and safe execution."""

from seal_sql.boundary import (
    SqlBoundaryResult,
    format_boundary_errors,
    validate_and_sanitize,
)
from seal_sql.dialects import Dialect, is_supported_dialect, to_sqlglot_dialect, transpile
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
from seal_sql.limits import (
    DEFAULT_MAX_JOINS,
    DEFAULT_MAX_ROWS,
    DEFAULT_MAX_SUBQUERY_DEPTH,
    SanitizerLimits,
)
from seal_sql.parse import (
    ParsedStatement,
    ParseFailure,
    parse_one_expression,
    parse_single_statement,
)
from seal_sql.planner_patterns import planner_sql_validation_error
from seal_sql.result import ColumnMetadata, QueryResult
from seal_sql.safety import (
    BlockedOperation,
    clamp_limits_and_offsets,
    enforce_limit_cap,
    find_blocked_operations,
    is_allowed_root,
    run_safety_checks,
    validate_limit_and_offset_literals,
)
from seal_sql.sanitizer import SanitizationResult, SQLSanitizer
from seal_sql.validator import SQLValidator, ValidationResult

__all__ = [
    # Boundary
    "SqlBoundaryResult",
    "validate_and_sanitize",
    "format_boundary_errors",
    # Dialects
    "Dialect",
    "is_supported_dialect",
    "to_sqlglot_dialect",
    "transpile",
    # Limits
    "SanitizerLimits",
    "DEFAULT_MAX_ROWS",
    "DEFAULT_MAX_JOINS",
    "DEFAULT_MAX_SUBQUERY_DEPTH",
    # Parse
    "ParseFailure",
    "ParsedStatement",
    "parse_single_statement",
    "parse_one_expression",
    # Planner pre-check
    "planner_sql_validation_error",
    # Safety
    "BlockedOperation",
    "find_blocked_operations",
    "validate_limit_and_offset_literals",
    "enforce_limit_cap",
    "clamp_limits_and_offsets",
    "run_safety_checks",
    "is_allowed_root",
    # Validator
    "SQLValidator",
    "ValidationResult",
    # Sanitizer
    "SQLSanitizer",
    "SanitizationResult",
    # Executor
    "QueryExecutor",
    "ExecutionConfig",
    "QueryExecutionError",
    "QueryTimeoutError",
    "DEFAULT_TIMEOUT_SECONDS",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_ROW_CAP",
    "DEFAULT_RETRY_BASE_DELAY",
    # Result
    "QueryResult",
    "ColumnMetadata",
]
