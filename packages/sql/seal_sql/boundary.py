"""Orchestrates schema validation and security sanitization (zero-trust boundary)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from seal_sql.limits import SanitizerLimits
from seal_sql.parse import ParseFailure, parse_single_statement
from seal_sql.sanitizer import SanitizationResult, SQLSanitizer
from seal_sql.validator import SQLValidator, ValidationResult

if TYPE_CHECKING:
    from seal_core.schema.models import DatabaseSchema


def format_boundary_errors(errors: list[str]) -> str:
    """Join boundary errors for exceptions and repair-loop feedback."""
    if not errors:
        return "SQL boundary failed"
    if len(errors) == 1:
        return errors[0]
    return "; ".join(errors)


_BOUNDARY_ERROR_MARKERS = (
    "Unknown column:",
    "Unknown table:",
    "Ambiguous column:",
    "SQL boundary failed",
    "SQL Sanitization failed:",
    "SQL parse error:",
    "Empty or unparseable SQL.",
    "Only a single SQL statement is allowed.",
)


def is_boundary_error_message(message: str) -> bool:
    """True when a raised exception message came from the SQL boundary layer."""
    return any(marker in message for marker in _BOUNDARY_ERROR_MARKERS)


@dataclass(frozen=True)
class SqlBoundaryResult:
    """Combined outcome of validator + sanitizer."""

    valid: bool
    executable_sql: str = ""
    validation: ValidationResult | None = None
    sanitization: SanitizationResult | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def from_parse_failure(cls, failure: ParseFailure) -> SqlBoundaryResult:
        return cls(
            valid=False,
            executable_sql=failure.source_sql,
            errors=[failure.message],
        )

    @classmethod
    def from_validation_failure(cls, result: ValidationResult) -> SqlBoundaryResult:
        return cls(
            valid=False,
            executable_sql=result.normalized_sql or "",
            validation=result,
            errors=list(result.errors),
            warnings=list(result.warnings),
        )

    @classmethod
    def from_sanitization_failure(
        cls, validation: ValidationResult, sanitization: SanitizationResult
    ) -> SqlBoundaryResult:
        detail = "; ".join(sanitization.blocked_operations) or "unknown reason"
        return cls(
            valid=False,
            executable_sql=sanitization.sanitized_sql,
            validation=validation,
            sanitization=sanitization,
            errors=[f"SQL Sanitization failed: {detail}"],
            warnings=list(validation.warnings),
        )

    @classmethod
    def success(
        cls, validation: ValidationResult, sanitization: SanitizationResult
    ) -> SqlBoundaryResult:
        return cls(
            valid=True,
            executable_sql=sanitization.sanitized_sql,
            validation=validation,
            sanitization=sanitization,
            warnings=list(validation.warnings) + list(sanitization.warnings),
        )


def validate_and_sanitize(
    sql: str,
    schema: DatabaseSchema,
    *,
    limits: SanitizerLimits | None = None,
) -> SqlBoundaryResult:
    """Parse once, validate schema, then sanitize — shared query/chat entry point."""
    parsed = parse_single_statement(sql, schema.dialect)
    if isinstance(parsed, ParseFailure):
        return SqlBoundaryResult.from_parse_failure(parsed)

    validation = SQLValidator(schema).validate_parsed(parsed)
    if not validation.valid:
        return SqlBoundaryResult.from_validation_failure(validation)

    effective_limits = limits or SanitizerLimits.from_settings()
    sanitization = SQLSanitizer(dialect=schema.dialect, limits=effective_limits).sanitize_parsed(
        parsed
    )
    if not sanitization.safe:
        return SqlBoundaryResult.from_sanitization_failure(validation, sanitization)

    return SqlBoundaryResult.success(validation, sanitization)
