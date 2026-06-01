import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { Callout } from '@/components/docs/callout';
import { DocsProse } from '@/components/docs/docs-prose';

export default function ZeroTrustSqlPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Zero-trust SQL boundary"
        description="How Seal parses, validates, and sanitizes every LLM-generated statement before it reaches your database."
      />

      <DocsProse>
        <p>
          Seal never executes raw SQL from a model. After{' '}
          <Link href="/docs/guardrails">guardrails</Link> allow a request, generated SQL passes through
          a <strong>SQLGlot AST pipeline</strong> in <code>packages/sql/</code>. Only then does the
          query executor run against Postgres or DuckDB.
        </p>

        <Callout variant="info" title="Guardrails vs SQL boundary">
          <strong>Guardrails</strong> decide whether the <em>question</em> belongs on a data analytics
          API. The <strong>zero-trust SQL boundary</strong> decides whether the <em>statement</em> is
          safe and schema-valid — even when the question is in scope.
        </Callout>

        <h2>Where it runs</h2>
        <p>
          Both <code>POST /v1/query</code> and chat SQL (when{' '}
          <code>ChatDecision.needs_data</code> is true) call the same function:{' '}
          <code>execute_natural_language_query</code> in <code>packages/core/seal_core/pipeline/</code>,
          which calls <code>validate_and_sanitize</code> in <code>packages/sql/seal_sql/boundary.py</code>{' '}
          (one SQLGlot parse, then schema validation and sanitization).
        </p>
        <pre className="not-prose overflow-x-auto rounded-xl border border-border/50 bg-muted/30 p-5 font-mono text-xs leading-relaxed text-foreground">
          {`Planner (LLM + Instructor → QueryPlan.sql)
    │
    ▼
validate_and_sanitize()  — parse once
    ├─ SQLValidator.validate_parsed   (tables / columns / ambiguity)
    └─ SQLSanitizer.sanitize_parsed   (read-only AST, LIMIT/OFFSET, complexity)
    │
    ▼
QueryExecutor  — timeout, retries, row cap (safety net)`}
        </pre>
        <p>
          Failed validation or sanitization feeds the <strong>repair loop</strong> (up to three
          attempts): errors are sent back to the planner so it can regenerate SQL. See{' '}
          <Link href="/docs/how-it-works">How it works</Link> for the full HTTP flow.
        </p>

        <h2>Layer 1 — Planner pre-check</h2>
        <p>
          <code>QueryPlan</code> (Pydantic + Instructor) applies fast regex checks before AST work:
          obvious DML/DDL keywords, multi-statement <code>;</code>, and statement-anchored patterns for{' '}
          <code>EXECUTE</code>, <code>CALL</code>, <code>ANALYZE</code>, etc. Column names such as{' '}
          <code>analyze</code> are allowed; standalone <code>ANALYZE users</code> is not.
        </p>
        <p>
          This layer is a hint for the LLM retry loop — not a security boundary on its own.
        </p>

        <h2>Layer 2 — SQLValidator (schema)</h2>
        <p>
          <code>SQLValidator</code> parses with SQLGlot using the target database{' '}
          <strong>dialect</strong> (<code>postgres</code> or <code>duckdb</code>), then:
        </p>
        <ul>
          <li>
            <strong>Syntax</strong> — unparseable SQL fails with a parse error (no execution).
          </li>
          <li>
            <strong>Tables</strong> — every <code>exp.Table</code> must exist in the introspected{' '}
            <code>DatabaseSchema</code> (CTEs and subquery aliases excluded).
          </li>
          <li>
            <strong>Columns</strong> — qualified columns and uniquely resolvable unqualified columns
            are checked against the schema. Unqualified columns that exist in more than one table in
            the <em>same SELECT scope</em> are rejected as ambiguous — including once per{' '}
            <code>UNION</code> branch (repair loop can fix with <code>u.id</code>).
          </li>
          <li>
            <strong>CTEs</strong> — CTE names are recognized as tables in scope; output columns of
            CTEs are not validated against the catalog (only base tables from introspection).
          </li>
          <li>
            <strong>Warnings</strong> — <code>SELECT *</code> produces a non-fatal warning returned
            on the API response.
          </li>
        </ul>

        <h2>Layer 3 — SQLSanitizer (security)</h2>
        <p>
          <code>SQLSanitizer</code> re-parses normalized SQL with the same dialect and enforces
          execution policy:
        </p>

        <h3>Read-only AST blocklist</h3>
        <p>
          A full-tree scan blocks destructive or session-changing expression types, including but not
          limited to:
        </p>
        <ul>
          <li>
            DML/DDL: <code>DROP</code>, <code>DELETE</code>, <code>UPDATE</code>, <code>INSERT</code>,{' '}
            <code>ALTER</code>, <code>CREATE</code>, <code>TRUNCATE</code>, <code>MERGE</code>
          </li>
          <li>
            Privilege / session: <code>GRANT</code>, <code>REVOKE</code>, <code>SET</code>,{' '}
            <code>PRAGMA</code>, <code>ATTACH</code>, <code>DETACH</code>, transactions
          </li>
          <li>
            Data movement: <code>COPY</code>, <code>SELECT … INTO</code> (<code>exp.Into</code>)
          </li>
          <li>
            Procedural / admin: <code>Command</code>, <code>Execute</code>, <code>Analyze</code>,{' '}
            <code>Refresh</code>
          </li>
          <li>
            Row locking: <code>FOR UPDATE</code>, <code>FOR SHARE</code> (<code>exp.Lock</code>)
          </li>
        </ul>
        <p>
          Nested writes in CTEs are caught (e.g.{' '}
          <code>WITH d AS (DELETE FROM orders …) SELECT …</code>).
        </p>

        <h3>Allowed statement shapes</h3>
        <p>
          The root AST node must be <code>Select</code>, <code>Union</code>, <code>Intersect</code>, or{' '}
          <code>Except</code> — not a bare <code>Command</code> or admin statement.
        </p>

        <h3>Single statement only</h3>
        <p>
          Multi-statement scripts (<code>SELECT 1; DROP TABLE users</code>) are rejected to reduce
          injection risk.
        </p>

        <h3>LIMIT and OFFSET policy</h3>
        <ul>
          <li>
            <strong>Dynamic LIMIT/OFFSET</strong> (e.g. <code>LIMIT (SELECT 1000)</code>) is rejected
            with an explicit error (distinct from negative literals).
          </li>
          <li>
            <strong>Negative literals</strong> (e.g. <code>LIMIT -1</code>) are rejected.
          </li>
          <li>
            Missing outer <code>LIMIT</code> → inject <code>LIMIT</code> up to{' '}
            <code>MAX_ROWS</code> (default 10,000; workspace/env configurable). Applies even when only{' '}
            <code>OFFSET</code> was present.
          </li>
          <li>
            Literal <code>LIMIT</code> above <code>MAX_ROWS</code> anywhere in the tree → clamped with
            a warning (including inner subqueries).
          </li>
          <li>
            <code>OFFSET</code> above <code>MAX_ROWS</code> (same cap as row limit) → rejected to
            avoid huge skip work before rows are returned.
          </li>
        </ul>

        <h3>Complexity bounds</h3>
        <ul>
          <li>
            <code>MAX_JOINS</code> — maximum <code>JOIN</code> clauses per query (default 10).
          </li>
          <li>
            <code>MAX_SUBQUERY_DEPTH</code> — maximum subquery nesting (default 5).
          </li>
        </ul>

        <h2>Layer 4 — QueryExecutor (runtime safety net)</h2>
        <p>
          Even after sanitization, the executor applies:
        </p>
        <ul>
          <li>Query timeout (<code>QUERY_TIMEOUT_SECONDS</code>)</li>
          <li>Retries with backoff for transient failures</li>
          <li>
            <strong>Row cap</strong> (<code>QUERY_ROW_CAP</code>) — truncates fetched rows if a limit
            were bypassed
          </li>
        </ul>
        <p>
          Use a <strong>read-only database role</strong> in production for defense in depth; the AST
          boundary is still required because default dev compose uses a superuser.
        </p>

        <h2>Configuration</h2>
        <p>Sanitizer limits are driven by environment / workspace settings:</p>
        <ul>
          <li>
            <code>MAX_ROWS</code> — sanitizer <code>LIMIT</code> injection and clamping
          </li>
          <li>
            <code>MAX_JOINS</code>, <code>MAX_SUBQUERY_DEPTH</code> — complexity rejection
          </li>
          <li>
            <code>QUERY_ROW_CAP</code>, <code>QUERY_TIMEOUT_SECONDS</code> — executor
          </li>
        </ul>
        <p>
          See <Link href="/docs/configuration">Configuration reference</Link> and{' '}
          <Link href="/docs/workspace">Workspace settings</Link> for hot-reload in dev.
        </p>

        <h2>What is not blocked here</h2>
        <ul>
          <li>
            Expensive but read-only functions (e.g. <code>pg_sleep</code>) — rely on timeout and DB
            permissions.
          </li>
          <li>
            Access to system catalogs — restrict with DB grants if needed.
          </li>
          <li>
            Out-of-scope <em>questions</em> — handled by{' '}
            <Link href="/docs/guardrails">guardrails</Link>, not this layer.
          </li>
        </ul>

        <h2>Code map</h2>
        <ul>
          <li>
            <code>packages/sql/seal_sql/boundary.py</code> — <code>validate_and_sanitize</code>{' '}
            orchestration
          </li>
          <li>
            <code>packages/sql/seal_sql/safety.py</code> — shared blocklist, LIMIT/OFFSET, complexity
          </li>
          <li>
            <code>packages/sql/seal_sql/limits.py</code> — <code>SanitizerLimits</code> from env
          </li>
          <li>
            <code>packages/sql/seal_sql/parse.py</code> — single-statement parsing
          </li>
          <li>
            <code>packages/sql/seal_sql/validator.py</code> — schema validation
          </li>
          <li>
            <code>packages/sql/seal_sql/sanitizer.py</code> — security sanitization
          </li>
          <li>
            <code>packages/sql/seal_sql/executor.py</code> — execution and row cap
          </li>
          <li>
            <code>packages/core/seal_core/pipeline/execute.py</code> — orchestration + repair loop
          </li>
        </ul>
        <p>
          Tests: <code>packages/sql/tests/test_validator.py</code>,{' '}
          <code>test_sanitizer.py</code>, <code>test_safety.py</code>. Contributor mirror:{' '}
          <code>docs/zero-trust-sql.md</code>.
        </p>

        <Callout variant="success" title="Related docs">
          <Link href="/docs/guardrails">Guardrails</Link> ·{' '}
          <Link href="/docs/how-it-works">How it works</Link> ·{' '}
          <Link href="/docs/features#sql-safety">Features</Link> ·{' '}
          <Link href="/docs/multi-database">Multi-database</Link>
        </Callout>
      </DocsProse>
    </div>
  );
}
