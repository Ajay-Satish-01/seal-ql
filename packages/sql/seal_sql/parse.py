"""Shared SQLGlot parsing helpers for validator and sanitizer."""

from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from seal_sql.dialects import to_sqlglot_dialect

_MULTI_STATEMENT_MSG = (
    "Multi-statement queries are not allowed. Only a single SELECT statement is permitted."
)


@dataclass(frozen=True)
class ParseFailure:
    """Failed to parse SQL into a single statement."""

    message: str
    source_sql: str


@dataclass(frozen=True)
class ParsedStatement:
    """A single successfully parsed SQL statement."""

    expression: exp.Expression
    dialect: str
    source_sql: str

    def normalized_sql(self) -> str:
        """Serialize the AST back to SQL for the configured dialect."""
        return self.expression.sql(dialect=self.dialect, pretty=False)


def parse_single_statement(sql: str, dialect: str) -> ParsedStatement | ParseFailure:
    """Parse exactly one SQL statement, or return a structured failure.

    All SQL entry points (validator, sanitizer, boundary) must use this function so
    multi-statement scripts are rejected explicitly before AST checks.
    """
    sqlglot_dialect = to_sqlglot_dialect(dialect)

    try:
        statements = sqlglot.parse(sql, dialect=sqlglot_dialect)
    except ParseError as exc:
        return ParseFailure(message=f"SQL parse error: {exc}", source_sql=sql)

    if len(statements) > 1:
        return ParseFailure(message=_MULTI_STATEMENT_MSG, source_sql=sql)

    if not statements or statements[0] is None:
        return ParseFailure(message="Empty or unparseable SQL.", source_sql=sql)

    expression = statements[0]
    if isinstance(expression, exp.Block):
        return ParseFailure(message=_MULTI_STATEMENT_MSG, source_sql=sql)

    return ParsedStatement(
        expression=expression,
        dialect=sqlglot_dialect,
        source_sql=sql,
    )


def parse_one_expression(sql: str, dialect: str) -> ParsedStatement | ParseFailure:
    """Deprecated alias for ``parse_single_statement``."""
    import warnings

    warnings.warn(
        "parse_one_expression is deprecated, use parse_single_statement instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return parse_single_statement(sql, dialect)
