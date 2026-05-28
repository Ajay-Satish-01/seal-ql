"""Intelligence SQL — SQL validation, sanitization, and safe execution."""

from intelligence_sql.dialects import Dialect, is_supported_dialect, to_sqlglot_dialect, transpile
from intelligence_sql.sanitizer import (
    DEFAULT_MAX_JOINS,
    DEFAULT_MAX_ROWS,
    DEFAULT_MAX_SUBQUERY_DEPTH,
    BlockedOperation,
    SanitizationResult,
    SQLSanitizer,
)
from intelligence_sql.validator import SQLValidator, ValidationResult

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
]
