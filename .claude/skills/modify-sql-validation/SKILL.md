---
name: modify-sql-validation
description: Step-by-step workflow for updating the SQL AST validation logic or modifying dialect constraints.
---

# Update SQL Validation Rules

1. **Identify the Dialect Constraint**
   Determine whether the safety update applies to DuckDB, Postgres, or TimescaleDB.

2. **Update AST Parser in `packages/sql/`**
   Add the new node check or blocklist rule to the SQLGlot validation engine.

3. **Write Injection Tests**
   Add malicious SQL generation attempts (e.g., `DROP TABLE`, infinite loops) to `packages/sql/tests/`.

4. **Run Isolated Tests**
   Execute `uv run pytest packages/sql/` to verify the AST parser successfully catches the injected payloads.

5. **Verify End-to-End**
   Spin up the stack (`make up`, `make seed`) and test against the API gateway to ensure the error propagates correctly to the client SDK.
