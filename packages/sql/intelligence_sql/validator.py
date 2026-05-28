"""SQL Validator — AST-based validation of LLM-generated SQL.

Parses SQL via SQLGlot, then validates that all referenced tables and columns
exist in the provided DatabaseSchema. This catches errors *before* the query
hits the database, giving us a chance to ask the LLM to repair.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from intelligence_sql.dialects import to_sqlglot_dialect

if TYPE_CHECKING:
    from intelligence_core.schema.models import DatabaseSchema


@dataclass(frozen=True)
class ValidationResult:
    """Result of SQL validation against a database schema.

    Attributes:
        valid: Whether the SQL passed all validation checks.
        errors: Human-readable error messages (empty if valid).
        warnings: Non-fatal issues (e.g., using SELECT *).
        normalized_sql: The SQL normalized by SQLGlot (or the original if parsing failed).
        tables_referenced: Set of table names found in the query.
        columns_referenced: Dict mapping table_name -> set of column names.
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    normalized_sql: str = ""
    tables_referenced: set[str] = field(default_factory=set)
    columns_referenced: dict[str, set[str]] = field(default_factory=dict)


class SQLValidator:
    """Validates SQL queries against a known database schema.

    Uses SQLGlot to parse the SQL into an AST, then walks the tree to
    extract table and column references. Each reference is checked against
    the provided DatabaseSchema.

    Example:
        >>> schema = DatabaseSchema(dialect="postgres", tables=[...])
        >>> validator = SQLValidator(schema)
        >>> result = validator.validate("SELECT name FROM users WHERE id = 1")
        >>> assert result.valid
    """

    def __init__(self, schema: DatabaseSchema) -> None:
        """Initialize the validator with a database schema.

        Args:
            schema: The database schema to validate against.
        """
        self._schema = schema
        self._dialect = to_sqlglot_dialect(schema.dialect)

        # Pre-build lookup indexes for fast validation.
        # Table names are lowercased for case-insensitive matching.
        self._table_names: set[str] = {t.name.lower() for t in schema.tables}
        self._table_columns: dict[str, set[str]] = {
            t.name.lower(): {c.name.lower() for c in t.columns} for t in schema.tables
        }

    def validate(self, sql: str) -> ValidationResult:
        """Validate a SQL query against the schema.

        Performs the following checks:
        1. SQL can be parsed by SQLGlot
        2. All referenced tables exist in the schema
        3. All referenced columns exist in their respective tables
        4. Warns on SELECT * usage

        Args:
            sql: The SQL query string to validate.

        Returns:
            A ValidationResult with validation outcome and details.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # --- Step 1: Parse ---
        try:
            parsed = sqlglot.parse_one(sql, dialect=self._dialect)
        except ParseError as e:
            return ValidationResult(
                valid=False,
                errors=[f"SQL parse error: {e}"],
                normalized_sql=sql,
            )

        # --- Step 2: Normalize ---
        normalized_sql = parsed.sql(dialect=self._dialect, pretty=False)

        # --- Step 3: Extract table references ---
        tables_referenced = self._extract_tables(parsed)

        # --- Step 4: Validate tables exist ---
        unknown_tables: set[str] = set()
        for table_name in tables_referenced:
            if table_name.lower() not in self._table_names:
                errors.append(
                    f"Unknown table: '{table_name}'. "
                    f"Available tables: {', '.join(sorted(self._table_names))}"
                )
                unknown_tables.add(table_name.lower())

        # --- Step 5: Extract and validate columns ---
        columns_referenced = self._extract_columns(parsed, tables_referenced)

        for table_name, cols in columns_referenced.items():
            if table_name == "_unresolved_":
                # These columns don't exist in any known table.
                for col in cols:
                    all_known_cols = set()
                    for table_cols in self._table_columns.values():
                        all_known_cols.update(table_cols)
                    errors.append(f"Unknown column: '{col}' — not found in any referenced table.")
                continue

            table_lower = table_name.lower()
            if table_lower in unknown_tables:
                # Don't validate columns for unknown tables — already errored.
                continue
            if table_lower not in self._table_columns:
                continue

            known_cols = self._table_columns[table_lower]
            for col in cols:
                if col.lower() not in known_cols:
                    errors.append(
                        f"Unknown column: '{col}' in table '{table_name}'. "
                        f"Available columns: {', '.join(sorted(known_cols))}"
                    )

        # --- Step 6: Warn on SELECT * ---
        if self._has_select_star(parsed):
            warnings.append(
                "Query uses SELECT * — consider selecting specific columns "
                "for better performance and clarity."
            )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            normalized_sql=normalized_sql,
            tables_referenced=tables_referenced,
            columns_referenced=columns_referenced,
        )

    def _extract_tables(self, parsed: exp.Expression) -> set[str]:
        """Extract all table names referenced in the query.

        Handles: FROM, JOIN, subqueries, CTEs.
        Filters out subquery aliases that aren't real tables.

        Args:
            parsed: The parsed SQLGlot expression.

        Returns:
            Set of table name strings.
        """
        tables: set[str] = set()

        for table_node in parsed.find_all(exp.Table):
            table_name = table_node.name
            if table_name:
                tables.add(table_name)

        # Also extract CTE names so we don't flag them as unknown tables.
        cte_names: set[str] = set()
        for cte in parsed.find_all(exp.CTE):
            alias = cte.alias
            if alias:
                cte_names.add(alias)

        # Subquery aliases aren't real tables either.
        subquery_aliases: set[str] = set()
        for subquery in parsed.find_all(exp.Subquery):
            alias = subquery.alias
            if alias:
                subquery_aliases.add(alias)

        # Remove CTE and subquery aliases — they aren't real tables.
        tables -= cte_names
        tables -= subquery_aliases

        return tables

    def _extract_columns(
        self, parsed: exp.Expression, known_tables: set[str]
    ) -> dict[str, set[str]]:
        """Extract column references grouped by table.

        When a column has an explicit table qualifier (e.g., `users.name`),
        it's assigned to that table. Unqualified columns are matched against
        all tables that contain a column with that name.

        Columns that cannot be resolved to any known table are placed under
        the special key '_unresolved_' for error reporting.

        Args:
            parsed: The parsed SQLGlot expression.
            known_tables: Table names found in the query.

        Returns:
            Dict mapping table_name -> set of column names.
        """
        columns: dict[str, set[str]] = {}

        for col_node in parsed.find_all(exp.Column):
            col_name = col_node.name
            table_ref = col_node.table

            if not col_name:
                continue

            if table_ref:
                # Explicit table qualifier — map directly.
                # Resolve alias to real table name if needed.
                real_table = self._resolve_table_alias(parsed, table_ref, known_tables)
                columns.setdefault(real_table, set()).add(col_name)
            else:
                # Unqualified column — try to find which table it belongs to.
                resolved = self._resolve_unqualified_column(col_name, known_tables)
                if resolved:
                    columns.setdefault(resolved, set()).add(col_name)
                else:
                    # Column not found in any referenced table — track for error.
                    # Only flag if the column doesn't exist in ANY known table.
                    col_lower = col_name.lower()
                    exists_anywhere = any(
                        col_lower in cols for cols in self._table_columns.values()
                    )
                    if not exists_anywhere:
                        columns.setdefault("_unresolved_", set()).add(col_name)

        return columns

    def _resolve_table_alias(
        self, parsed: exp.Expression, alias: str, known_tables: set[str]
    ) -> str:
        """Resolve a table alias back to the real table name.

        Args:
            parsed: The parsed expression tree.
            alias: The alias to resolve.
            known_tables: Known table names from the query.

        Returns:
            The real table name, or the alias itself if no mapping is found.
        """
        # Check if alias is already a known table name.
        if alias in known_tables:
            return alias

        # Walk FROM/JOIN clauses to find alias -> table mappings.
        for table_node in parsed.find_all(exp.Table):
            table_alias = table_node.alias
            if table_alias and table_alias.lower() == alias.lower():
                return table_node.name

        return alias

    def _resolve_unqualified_column(self, col_name: str, known_tables: set[str]) -> str | None:
        """Try to resolve an unqualified column to a table.

        If the column exists in exactly one of the referenced tables,
        assign it there. If ambiguous (exists in multiple), skip validation
        (the database will resolve it).

        Args:
            col_name: The column name to resolve.
            known_tables: Tables referenced in the query.

        Returns:
            The table name if uniquely resolved, None otherwise.
        """
        col_lower = col_name.lower()
        candidates: list[str] = []

        for table in known_tables:
            table_lower = table.lower()
            if table_lower in self._table_columns and col_lower in self._table_columns[table_lower]:
                candidates.append(table)

        if len(candidates) == 1:
            return candidates[0]

        # Ambiguous or not found — skip column validation for this one.
        return None

    def _has_select_star(self, parsed: exp.Expression) -> bool:
        """Check if the query uses SELECT *.

        Args:
            parsed: The parsed expression.

        Returns:
            True if SELECT * is used anywhere.
        """
        for _star in parsed.find_all(exp.Star):
            return True
        return False
