# Zero-trust SQL boundary

User-facing guide: docs site `/docs/zero-trust-sql`.

## Purpose

Every LLM-generated statement is parsed with **SQLGlot** before execution. Guardrails scope the *question*; this boundary scopes the *SQL*.

## Pipeline

`validate_and_sanitize` in `packages/sql/seal_sql/boundary.py` (called from `execute_natural_language_query`):

1. **QueryPlan** — Pydantic regex via `seal_sql/planner_patterns.py` (not sufficient alone)
2. **parse_single_statement** — single SQLGlot parse (rejects multi-statement scripts)
3. **SQLValidator.validate_parsed** — table/column schema checks
4. **SQLSanitizer.sanitize_parsed** — read-only AST, LIMIT/OFFSET, complexity
5. **QueryExecutor** — timeout, retries, row cap

## SQLValidator

- Parse with `schema.dialect` (`postgres` | `duckdb`)
- Reject unknown tables/columns; ambiguous unqualified columns per SELECT scope (one error per UNION branch)
- CTE aliases in scope; CTE output columns not catalog-validated
- Warn on `SELECT *`

## SQLSanitizer

- Tree-wide block: DML/DDL, `COPY`, `INTO`, `Lock`, `Command`, `Execute`, etc. (`packages/sql/seal_sql/safety.py`)
- Root must be `Select` | `Union` | `Intersect` | `Except`
- No multi-statement scripts
- Reject dynamic/negative LIMIT/OFFSET; reject OFFSET > `MAX_ROWS`; clamp all literal LIMITs > `MAX_ROWS`; inject root LIMIT when missing
- `MAX_JOINS`, `MAX_SUBQUERY_DEPTH`

## Configuration

- `MAX_ROWS`, `MAX_JOINS`, `MAX_SUBQUERY_DEPTH` — sanitizer
- `QUERY_ROW_CAP`, `QUERY_TIMEOUT_SECONDS` — executor

## Tests

`uv run pytest packages/sql/tests/ packages/core/tests/test_pipeline_safety.py packages/core/tests/test_planner_models.py`
