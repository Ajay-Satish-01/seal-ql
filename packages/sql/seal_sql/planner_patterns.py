"""Planner-level SQL pre-checks (regex). AST sanitization remains authoritative."""

from __future__ import annotations

import re

# Word-boundary DML/DDL keywords (unlikely as column names).
_DML_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|MERGE|COPY|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

# Statement-anchored admin/procedural keywords (avoids rejecting columns like `analyze`).
_STATEMENT_PATTERN = re.compile(
    r"(?i)(?:^|;)\s*(?:EXECUTE|CALL|VACUUM|ANALYZE|REFRESH|ATTACH|DETACH|PRAGMA)\b"
)

# Multi-statement: semicolon followed by a SQL keyword (ignores `;` inside string literals
# like `SELECT 'hello;world'`).  Only looks for statement-starting keywords after the `;`.
_MULTI_STATEMENT_PATTERN = re.compile(
    r";\s*(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|WITH|EXPLAIN|SET|GRANT|REVOKE"
    r"|TRUNCATE|EXECUTE|CALL|ANALYZE|ATTACH|DETACH|PRAGMA|COPY|MERGE)\b",
    re.IGNORECASE,
)

PLANNER_BLOCKED_SQL_PATTERNS: tuple[re.Pattern[str], ...] = (
    _DML_PATTERN,
    _STATEMENT_PATTERN,
    _MULTI_STATEMENT_PATTERN,
)


def planner_sql_validation_error(sql: str) -> str | None:
    """Return an error message if planner SQL fails regex pre-check, else None."""
    for pattern in PLANNER_BLOCKED_SQL_PATTERNS:
        match = pattern.search(sql)
        if match:
            return (
                f"Generated SQL contains a blocked pattern: '{match.group()}'. "
                "Only read-only SELECT queries are allowed."
            )
    return None
