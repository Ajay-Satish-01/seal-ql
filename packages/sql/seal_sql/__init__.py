"""Seal SQL — validation, sanitization, and safe execution."""

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
from seal_sql.result import ColumnMetadata, QueryResult
from seal_sql.sanitizer import (
    DEFAULT_MAX_JOINS,
    DEFAULT_MAX_ROWS,
    DEFAULT_MAX_SUBQUERY_DEPTH,
    BlockedOperation,
    SanitizationResult,
    SQLSanitizer,
)
from seal_sql.validator import SQLValidator, ValidationResult

__all__ = [
    # Dialects
    "Dialect",
    "is_supported_dialect",
    "to_sqlglot_dialect",
    "transpile",
    # Validator
    "SQLValidator",
    "ValidationResult",
    # Sanitizer
    "SQLSanitizer",
    "SanitizationResult",
    "BlockedOperation",
    "DEFAULT_MAX_ROWS",
    "DEFAULT_MAX_JOINS",
    "DEFAULT_MAX_SUBQUERY_DEPTH",
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
