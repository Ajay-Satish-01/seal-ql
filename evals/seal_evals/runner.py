"""Evaluation harness for the Query Planner against a JSONL dataset."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from seal_core.planner.planner import QueryPlanner
from seal_core.schema.introspector import get_introspector
from seal_core.schema.models import DatabaseSchema
from seal_core.settings import get_settings
from seal_sql.boundary import format_boundary_errors, validate_and_sanitize
from seal_sql.executor import QueryExecutor

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

logger = logging.getLogger(__name__)

DEFAULT_EVAL_PATH = Path(__file__).resolve().parent.parent / "data" / "eval_set.jsonl"
DEFAULT_EVAL_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/seal"
DEFAULT_MIN_RATE = 0.6
MAX_ATTEMPTS = 3
_LLM_BUFFER_SECONDS = 120.0

_EVAL_CASE_KEYS = frozenset({"question", "should_fail"})

# Sync guard: evals/tests/test_default_eval_set_case_count asserts the JSONL matches these.
EVAL_SET_EXPECTED_TOTAL = 27
EVAL_SET_EXPECTED_SHOULD_FAIL = 5


class EvalCase(TypedDict):
    question: str
    should_fail: bool


_METRIC_KEYS = (
    "total_queries",
    "scored_queries",
    "execution_success",
    "validation_success",
    "expected_failures_caught",
    "repair_successes",
    "timeouts",
)


def default_query_timeout() -> float:
    """Per-case timeout: execution budget × attempts plus buffer for planner/repair LLM calls."""
    settings = get_settings()
    return settings.query_timeout_seconds * MAX_ATTEMPTS + _LLM_BUFFER_SECONDS


def empty_metrics() -> dict[str, Any]:
    """Fresh counter dict for an eval run."""
    base: dict[str, Any] = dict.fromkeys(_METRIC_KEYS, 0)
    base["errors"] = []
    return base


def dialect_for_url(db_url: str) -> str:
    """Infer SQL dialect from a database URL."""
    lowered = db_url.strip().lower()
    if "postgres" in lowered or "postgresql" in lowered:
        return "postgres"
    return "duckdb"


def is_in_memory_url(db_url: str) -> bool:
    """True when the URL targets ephemeral storage (empty schema fallback allowed)."""
    normalized = db_url.strip().lower()
    if normalized in (":memory:", ""):
        return True
    return normalized.startswith("duckdb:///:memory:")


def _parse_float_arg(value: str, *, name: str) -> float:
    """Parse a CLI string into float (argparse type= hooks receive strings)."""
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(f"{name} must be a number, got {value!r}") from exc


def clamp_min_rate(value: str) -> float:
    """Validate --min-execution-rate is within [0, 1]."""
    rate = _parse_float_arg(value, name="min-execution-rate")
    if not 0.0 <= rate <= 1.0:
        raise argparse.ArgumentTypeError(
            f"min-execution-rate must be between 0 and 1 inclusive, got {rate}"
        )
    return rate


def parse_csv_list(value: str) -> list[str]:
    """Split a comma-separated CLI value into non-empty tokens."""
    return [part.strip() for part in value.split(",") if part.strip()]


def require_non_empty_csv(value: str, *, flag_name: str) -> list[str]:
    """Parse a comma-separated CLI flag and reject empty lists."""
    items = parse_csv_list(value)
    if not items:
        raise ValueError(f"{flag_name} must list at least one value")
    return items


_SENSITIVE_QUERY_KEYS = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "token",
        "auth",
        "secret",
        "access_token",
        "api_key",
        "api-key",
    }
)


def _redact_query_params(query: str) -> str:
    """Mask sensitive query-string values for safe logging/output."""
    if not query:
        return query
    redacted_pairs: list[tuple[str, str]] = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        if key.lower() in _SENSITIVE_QUERY_KEYS:
            redacted_pairs.append((key, "***"))
        else:
            redacted_pairs.append((key, value))
    return urlencode(redacted_pairs)


def redact_database_url(db_url: str) -> str:
    """Redact credentials from a database URL for logs and JSON output."""
    try:
        parsed = urlparse(db_url)
    except ValueError:
        return "<invalid-url>"

    if not parsed.scheme and not parsed.netloc:
        return db_url

    username = parsed.username
    hostname = parsed.hostname
    if not hostname and not parsed.path:
        return db_url

    netloc = parsed.netloc
    has_credentials = username is not None or parsed.password is not None
    if has_credentials:
        host_part = hostname or ""
        if parsed.port is not None:
            host_part = f"{host_part}:{parsed.port}"
        netloc = f"***:***@{host_part}"

    query = _redact_query_params(parsed.query)
    return urlunparse(parsed._replace(netloc=netloc, query=query))


def clamp_positive_timeout(value: str) -> float:
    """Validate --query-timeout is positive."""
    timeout = _parse_float_arg(value, name="query-timeout")
    if timeout <= 0:
        raise argparse.ArgumentTypeError(f"query-timeout must be positive, got {timeout}")
    return timeout


def summarize_metrics(metrics: dict[str, Any], *, planner_only: bool) -> dict[str, Any]:
    """Attach rates (denominator excludes should_fail cases) and mode."""
    scored = int(metrics.get("scored_queries", 0))
    execution_success = int(metrics.get("execution_success", 0))
    validation_success = int(metrics.get("validation_success", 0))
    errors = metrics.get("errors", [])
    error_count = len(errors) if isinstance(errors, list) else 0

    success = validation_success if planner_only else execution_success
    rate_key = "validation_rate" if planner_only else "execution_rate"
    rate = (success / scored) if scored > 0 else 0.0

    return {
        **metrics,
        "planner_only": planner_only,
        rate_key: round(rate, 4),
        "error_count": error_count,
    }


def should_exit_nonzero(
    summary: dict[str, Any],
    *,
    min_rate: float,
    planner_only: bool,
) -> bool:
    """Return True when the run should exit with code 1."""
    if summary.get("error_count", 0) > 0:
        return True
    if int(summary.get("scored_queries", 0)) == 0:
        return True
    rate_key = "validation_rate" if planner_only else "execution_rate"
    return float(summary.get(rate_key, 0.0)) < min_rate


def _parse_eval_row(row: dict[str, Any], *, line_no: int, path: Path) -> EvalCase:
    """Validate one JSONL object into a typed eval case."""
    extra = set(row.keys()) - _EVAL_CASE_KEYS
    if extra:
        names = ", ".join(sorted(extra))
        raise ValueError(f"Line {line_no} of {path}: unknown field(s): {names}")

    if "question" not in row:
        raise ValueError(f"Line {line_no} of {path}: missing required field 'question'")
    question = row["question"]
    if not isinstance(question, str):
        kind = type(question).__name__
        raise ValueError(f"Line {line_no} of {path}: 'question' must be a string, got {kind}")
    if not question.strip():
        raise ValueError(f"Line {line_no} of {path}: 'question' must be non-empty")

    if "should_fail" not in row:
        raise ValueError(f"Line {line_no} of {path}: missing required field 'should_fail'")
    should_fail = row["should_fail"]
    if not isinstance(should_fail, bool):
        kind = type(should_fail).__name__
        raise ValueError(f"Line {line_no} of {path}: 'should_fail' must be a boolean, got {kind}")

    return EvalCase(question=question, should_fail=should_fail)


def iter_eval_cases(path: Path) -> Iterator[EvalCase]:
    """Yield validated JSONL rows; skip blanks; wrap JSON errors with line numbers."""
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_no} of {path}: {exc}") from exc
            if not isinstance(row, dict):
                kind = type(row).__name__
                raise ValueError(f"Line {line_no} of {path}: expected JSON object, got {kind}")
            yield _parse_eval_row(row, line_no=line_no, path=path)


class EvalRunner:
    def __init__(
        self,
        db_url: str,
        dialect: str,
        *,
        planner_only: bool = False,
        query_timeout: float | None = None,
        model: str | None = None,
    ) -> None:
        self.db_url = db_url
        self.dialect = dialect
        self.planner_only = planner_only
        self.query_timeout = query_timeout if query_timeout is not None else default_query_timeout()
        self.model = model
        self.planner = QueryPlanner(model=model)
        self.executor = QueryExecutor(dialect, db_url)
        self.introspector = get_introspector(dialect, db_url)

    @asynccontextmanager
    async def _resources(self) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await self.executor.close()
            await self.introspector.close()

    async def load_schema(self) -> DatabaseSchema:
        """Introspect the target database; fail fast when a real URL is unreachable."""
        logger.info("Introspecting schema from %s...", self.db_url)
        try:
            return await self.introspector.introspect()
        except Exception as exc:
            if is_in_memory_url(self.db_url):
                logger.warning(
                    "Introspection failed for in-memory URL, using empty schema: %s",
                    exc,
                )
                return DatabaseSchema(dialect=self.dialect, tables=[])
            raise ConnectionError(f"Failed to introspect schema at {self.db_url}: {exc}") from exc

    def _record_timeout(
        self,
        metrics: dict[str, Any],
        *,
        question: str,
        should_fail: bool,
    ) -> None:
        """Record a per-case timeout. Scored cases count as failures (no success increment)."""
        metrics["timeouts"] += 1
        if should_fail:
            metrics["expected_failures_caught"] += 1
        else:
            metrics["errors"].append(
                f"Query '{question}' timed out after {self.query_timeout:.0f}s"
            )
        logger.error("Timed out: %s", question)

    async def _run_eval_case(
        self,
        case: EvalCase,
        schema: DatabaseSchema,
        metrics: dict[str, Any],
    ) -> None:
        """Run one case with timeout; cancel the task so asyncio can propagate cancellation."""
        question = case["question"]
        should_fail = case["should_fail"]
        task = asyncio.create_task(self._evaluate_query(case, schema, metrics))
        try:
            await asyncio.wait_for(task, timeout=self.query_timeout)
        except TimeoutError:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            self._record_timeout(metrics, question=question, should_fail=should_fail)

    async def run_evals(
        self,
        jsonl_path: str | Path,
        *,
        schema: DatabaseSchema | None = None,
    ) -> dict[str, Any]:
        path = Path(jsonl_path)
        if not path.exists():
            raise FileNotFoundError(f"Eval set not found at {path}")

        metrics = empty_metrics()

        async with self._resources():
            loaded_schema = schema if schema is not None else await self.load_schema()
            for case in iter_eval_cases(path):
                metrics["total_queries"] += 1
                await self._run_eval_case(case, loaded_schema, metrics)

        return summarize_metrics(metrics, planner_only=self.planner_only)

    async def _evaluate_query(
        self,
        case: EvalCase,
        schema: DatabaseSchema,
        metrics: dict[str, Any],
    ) -> None:
        question = case["question"]
        should_fail = case["should_fail"]

        # Scored cases increment before work so timeouts count against the rate denominator.
        if not should_fail:
            metrics["scored_queries"] += 1

        logger.info("Evaluating query: %s", question)

        plan = None
        last_error: Exception | None = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                if plan is None:
                    plan = await self.planner.generate_plan(schema, question)
                else:
                    plan = await self.planner.repair_plan(question, plan.sql, str(last_error))
                    metrics["repair_successes"] += 1

                boundary = validate_and_sanitize(plan.sql, schema)
                if not boundary.valid:
                    raise ValueError(format_boundary_errors(boundary.errors))

                if should_fail:
                    metrics["errors"].append(
                        f"Query '{question}' was expected to fail but passed validation."
                    )
                    break

                if self.planner_only:
                    metrics["validation_success"] += 1
                    break

                await self.executor.execute(boundary.executable_sql)
                metrics["validation_success"] += 1
                metrics["execution_success"] += 1
                break

            except Exception as exc:
                last_error = exc
                if attempt >= MAX_ATTEMPTS:
                    if should_fail:
                        metrics["expected_failures_caught"] += 1
                    else:
                        metrics["errors"].append(
                            f"Query '{question}' failed after {MAX_ATTEMPTS} attempts: {exc}"
                        )
                    break


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Seal planner evals against a JSONL dataset.")
    parser.add_argument(
        "database_url",
        nargs="?",
        default=DEFAULT_EVAL_DATABASE_URL,
        help=f"SQLAlchemy URL (default: seeded local Postgres, {DEFAULT_EVAL_DATABASE_URL})",
    )
    parser.add_argument(
        "--jsonl",
        type=Path,
        default=DEFAULT_EVAL_PATH,
        help=f"Path to eval JSONL (default: {DEFAULT_EVAL_PATH})",
    )
    parser.add_argument(
        "--planner-only",
        action="store_true",
        help="Validate generated SQL only; do not execute against the database",
    )
    parser.add_argument(
        "--min-execution-rate",
        type=clamp_min_rate,
        default=DEFAULT_MIN_RATE,
        metavar="RATE",
        help=f"Exit 1 if success rate is below RATE (default: {DEFAULT_MIN_RATE})",
    )
    parser.add_argument(
        "--query-timeout",
        type=clamp_positive_timeout,
        default=None,
        metavar="SECONDS",
        help=(
            "Max seconds per eval case (default: query_timeout_seconds × "
            f"{MAX_ATTEMPTS} + {_LLM_BUFFER_SECONDS:.0f})"
        ),
    )
    parser.add_argument(
        "--models",
        type=str,
        default=None,
        metavar="MODELS",
        help=(
            "Comma-separated LiteLLM model identifiers for side-by-side comparison "
            "(default: settings LLM_MODEL)"
        ),
    )
    parser.add_argument(
        "--dialect-urls",
        type=str,
        default=None,
        metavar="URLS",
        help=(
            "Comma-separated database URLs for dialect comparison "
            "(default: positional database_url)"
        ),
    )
    return parser


def resolved_models(models_arg: str | None) -> list[str | None]:
    """Return model list for matrix runs; None means settings default."""
    if not models_arg:
        return [None]
    return require_non_empty_csv(models_arg, flag_name="--models")


def resolved_dialect_urls(
    dialect_urls_arg: str | None,
    *,
    positional_url: str,
) -> list[str]:
    """Return database URLs for matrix runs."""
    if dialect_urls_arg:
        return require_non_empty_csv(dialect_urls_arg, flag_name="--dialect-urls")
    if not positional_url.strip():
        raise ValueError("database_url is required")
    return [positional_url]


def run_label(*, db_url: str, dialect: str, model: str | None) -> dict[str, str]:
    """Stable metadata for one matrix leg."""
    resolved_model = model or get_settings().resolved_llm_model
    return {
        "database_url_redacted": redact_database_url(db_url),
        "dialect": dialect,
        "model": resolved_model,
    }


async def load_schema_for_url(
    db_url: str,
    dialect: str,
    *,
    query_timeout: float | None,
) -> DatabaseSchema:
    """Introspect once per database URL for matrix runs."""
    runner = EvalRunner(
        db_url,
        dialect,
        planner_only=True,
        query_timeout=query_timeout,
    )
    async with runner._resources():
        return await runner.load_schema()


async def run_eval_matrix(
    *,
    database_urls: list[str],
    models: list[str | None],
    jsonl_path: Path,
    planner_only: bool,
    query_timeout: float | None,
) -> dict[str, Any]:
    """Run evals for each dialect URL × model combination."""
    if not models:
        raise ValueError("--models must list at least one model")
    if not database_urls:
        raise ValueError("--dialect-urls must list at least one database URL")

    runs: list[dict[str, Any]] = []
    schema_cache: dict[str, DatabaseSchema] = {}

    for db_url in database_urls:
        dialect = dialect_for_url(db_url)
        if db_url not in schema_cache:
            schema_cache[db_url] = await load_schema_for_url(
                db_url,
                dialect,
                query_timeout=query_timeout,
            )
        schema = schema_cache[db_url]

        for model in models:
            runner = EvalRunner(
                db_url,
                dialect,
                planner_only=planner_only,
                query_timeout=query_timeout,
                model=model,
            )
            label = run_label(db_url=db_url, dialect=dialect, model=model)
            logger.info(
                "Matrix leg: dialect=%s model=%s url=%s",
                label["dialect"],
                label["model"],
                label["database_url_redacted"],
            )
            metrics = await runner.run_evals(jsonl_path, schema=schema)
            runs.append({**label, **metrics})

    return {
        "comparison": True,
        "planner_only": planner_only,
        "runs": runs,
    }


def failed_matrix_legs(
    matrix: dict[str, Any],
    *,
    min_rate: float,
    planner_only: bool,
) -> list[dict[str, Any]]:
    """Return matrix legs that failed thresholds."""
    runs = matrix.get("runs")
    if not isinstance(runs, list):
        return []

    rate_key = "validation_rate" if planner_only else "execution_rate"
    failed: list[dict[str, Any]] = []
    for run in runs:
        if not isinstance(run, dict):
            continue
        if not should_exit_nonzero(run, min_rate=min_rate, planner_only=planner_only):
            continue
        failed.append(
            {
                "dialect": run.get("dialect"),
                "model": run.get("model"),
                "database_url_redacted": run.get("database_url_redacted"),
                rate_key: run.get(rate_key),
                "error_count": run.get("error_count"),
                "scored_queries": run.get("scored_queries"),
            }
        )
    return failed


def matrix_should_exit_nonzero(
    matrix: dict[str, Any],
    *,
    min_rate: float,
    planner_only: bool,
) -> bool:
    """Exit non-zero when any matrix leg fails thresholds."""
    runs = matrix.get("runs")
    if not isinstance(runs, list) or not runs:
        return True
    return bool(failed_matrix_legs(matrix, min_rate=min_rate, planner_only=planner_only))


async def _async_main(args: argparse.Namespace) -> int:
    logging.basicConfig(level=logging.INFO)
    try:
        models = resolved_models(args.models)
        database_urls = resolved_dialect_urls(
            args.dialect_urls,
            positional_url=args.database_url,
        )
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    is_matrix = len(models) > 1 or len(database_urls) > 1

    try:
        if is_matrix:
            results = await run_eval_matrix(
                database_urls=database_urls,
                models=models,
                jsonl_path=args.jsonl,
                planner_only=args.planner_only,
                query_timeout=args.query_timeout,
            )
        else:
            dialect = dialect_for_url(database_urls[0])
            runner = EvalRunner(
                database_urls[0],
                dialect,
                planner_only=args.planner_only,
                query_timeout=args.query_timeout,
                model=models[0],
            )
            results = await runner.run_evals(args.jsonl)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1
    except (ConnectionError, ValueError) as exc:
        logger.error("%s", exc)
        return 1

    print("\n=== Eval Results ===")
    print(json.dumps(results, indent=2))

    if is_matrix:
        failed = matrix_should_exit_nonzero(
            results,
            min_rate=args.min_execution_rate,
            planner_only=args.planner_only,
        )
    else:
        failed = should_exit_nonzero(
            results,
            min_rate=args.min_execution_rate,
            planner_only=args.planner_only,
        )

    if failed:
        if is_matrix:
            for leg in failed_matrix_legs(
                results,
                min_rate=args.min_execution_rate,
                planner_only=args.planner_only,
            ):
                rate_key = "validation_rate" if args.planner_only else "execution_rate"
                logger.error(
                    "Matrix leg failed: dialect=%s model=%s url=%s %s=%s scored=%s errors=%s",
                    leg.get("dialect"),
                    leg.get("model"),
                    leg.get("database_url_redacted"),
                    rate_key,
                    leg.get(rate_key),
                    leg.get("scored_queries"),
                    leg.get("error_count"),
                )
            logger.error(
                "Matrix eval failed: one or more legs below min rate %s",
                args.min_execution_rate,
            )
        else:
            rate_key = "validation_rate" if args.planner_only else "execution_rate"
            logger.error(
                "Eval failed: error_count=%s timeouts=%s %s=%s scored=%s (min=%s)",
                results.get("error_count"),
                results.get("timeouts"),
                rate_key,
                results.get(rate_key),
                results.get("scored_queries"),
                args.min_execution_rate,
            )
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    return asyncio.run(_async_main(args))


if __name__ == "__main__":
    sys.exit(main())
