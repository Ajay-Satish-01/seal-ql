"""Unit tests for eval runner helpers and query loop edge cases."""

from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from seal_core.planner.models import QueryPlan
from seal_core.schema.models import DatabaseSchema
from seal_evals.runner import (
    DEFAULT_EVAL_DATABASE_URL,
    EVAL_SET_EXPECTED_SHOULD_FAIL,
    EVAL_SET_EXPECTED_TOTAL,
    EvalRunner,
    build_arg_parser,
    clamp_min_rate,
    clamp_positive_timeout,
    default_query_timeout,
    dialect_for_url,
    empty_metrics,
    failed_matrix_legs,
    is_in_memory_url,
    iter_eval_cases,
    matrix_should_exit_nonzero,
    parse_csv_list,
    redact_database_url,
    require_non_empty_csv,
    resolved_dialect_urls,
    resolved_models,
    run_eval_matrix,
    should_exit_nonzero,
    summarize_metrics,
)
from seal_sql.boundary import SqlBoundaryResult


def test_empty_metrics_shape() -> None:
    metrics = empty_metrics()
    assert metrics["errors"] == []
    assert metrics["scored_queries"] == 0
    assert metrics["timeouts"] == 0


def test_summarize_metrics_uses_scored_denominator() -> None:
    summary = summarize_metrics(
        {
            "total_queries": 20,
            "scored_queries": 17,
            "execution_success": 15,
            "validation_success": 16,
            "errors": [],
        },
        planner_only=False,
    )
    assert summary["execution_rate"] == round(15 / 17, 4)


def test_summarize_metrics_planner_only_mode() -> None:
    summary = summarize_metrics(
        {
            "scored_queries": 4,
            "validation_success": 3,
            "errors": [],
        },
        planner_only=True,
    )
    assert summary["validation_rate"] == 0.75


def test_should_exit_on_errors() -> None:
    summary = summarize_metrics(
        {
            "scored_queries": 5,
            "execution_success": 5,
            "validation_success": 5,
            "errors": ["failure"],
        },
        planner_only=False,
    )
    assert should_exit_nonzero(summary, min_rate=0.0, planner_only=False) is True


def test_should_exit_below_min_rate() -> None:
    summary = summarize_metrics(
        {"scored_queries": 10, "execution_success": 5, "validation_success": 10, "errors": []},
        planner_only=False,
    )
    assert should_exit_nonzero(summary, min_rate=0.8, planner_only=False) is True
    assert should_exit_nonzero(summary, min_rate=0.5, planner_only=False) is False


def test_should_exit_zero_scored_queries() -> None:
    summary = summarize_metrics(
        {"scored_queries": 0, "execution_success": 0, "validation_success": 0, "errors": []},
        planner_only=False,
    )
    assert should_exit_nonzero(summary, min_rate=0.0, planner_only=False) is True


def test_dialect_for_url() -> None:
    assert dialect_for_url("postgresql+asyncpg://localhost/seal") == "postgres"
    assert dialect_for_url("postgres://user@host/db") == "postgres"
    assert dialect_for_url("duckdb:///data/x.duckdb") == "duckdb"


def test_is_in_memory_url() -> None:
    assert is_in_memory_url(":memory:") is True
    assert is_in_memory_url("duckdb:///:memory:") is True
    assert is_in_memory_url("postgresql+asyncpg://localhost/seal") is False
    assert is_in_memory_url("duckdb:///data/memory_backup.duckdb") is False


def test_clamp_min_rate_rejects_out_of_range() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        clamp_min_rate("1.5")
    assert clamp_min_rate("0.6") == 0.6


def test_clamp_positive_timeout() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        clamp_positive_timeout("0")
    assert clamp_positive_timeout("60") == 60.0


def test_default_query_timeout_positive() -> None:
    assert default_query_timeout() > 0


def test_iter_eval_cases_skips_blanks(tmp_path: Path) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text(
        '{"question": "one", "should_fail": false}\n\n{"question": "two", "should_fail": true}\n',
        encoding="utf-8",
    )
    rows = list(iter_eval_cases(path))
    assert len(rows) == 2


def test_iter_eval_cases_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text("not json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 1"):
        list(iter_eval_cases(path))


def test_iter_eval_cases_rejects_wrong_types(tmp_path: Path) -> None:
    path = tmp_path / "types.jsonl"
    path.write_text('{"question": 1, "should_fail": false}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="'question' must be a string"):
        list(iter_eval_cases(path))


def test_iter_eval_cases_rejects_missing_should_fail(tmp_path: Path) -> None:
    path = tmp_path / "missing.jsonl"
    path.write_text('{"question": "count rows"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="missing required field 'should_fail'"):
        list(iter_eval_cases(path))


def test_iter_eval_cases_rejects_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / "extra.jsonl"
    path.write_text(
        '{"question": "ok", "should_fail": false, "expected_fail": true}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown field"):
        list(iter_eval_cases(path))


def test_build_arg_parser_default_database_url() -> None:
    args = build_arg_parser().parse_args([])
    assert args.database_url == DEFAULT_EVAL_DATABASE_URL


def test_parse_csv_list() -> None:
    assert parse_csv_list("a,b, c") == ["a", "b", "c"]
    assert parse_csv_list("  ") == []


def test_resolved_models_default() -> None:
    assert resolved_models(None) == [None]


def test_resolved_models_csv() -> None:
    assert resolved_models("m1,m2") == ["m1", "m2"]


def test_resolved_dialect_urls_positional() -> None:
    assert resolved_dialect_urls(None, positional_url="postgres://x") == ["postgres://x"]


def test_resolved_dialect_urls_csv() -> None:
    urls = resolved_dialect_urls("u1,u2", positional_url="ignored")
    assert urls == ["u1", "u2"]


def test_matrix_should_exit_when_any_leg_fails() -> None:
    matrix = {
        "comparison": True,
        "runs": [
            {"scored_queries": 5, "execution_success": 5, "validation_success": 5, "errors": []},
            {"scored_queries": 5, "execution_success": 2, "validation_success": 5, "errors": []},
        ],
    }
    assert matrix_should_exit_nonzero(matrix, min_rate=0.8, planner_only=False) is True


def test_default_eval_set_case_count() -> None:
    """Keep eval_set.jsonl in sync with EVAL_SET_EXPECTED_* constants."""
    from seal_evals.runner import DEFAULT_EVAL_PATH

    cases = list(iter_eval_cases(DEFAULT_EVAL_PATH))
    assert len(cases) == EVAL_SET_EXPECTED_TOTAL
    assert sum(1 for case in cases if case["should_fail"]) == EVAL_SET_EXPECTED_SHOULD_FAIL


def test_require_non_empty_csv_rejects_blank() -> None:
    with pytest.raises(ValueError, match="--models"):
        require_non_empty_csv("  ", flag_name="--models")


def test_resolved_models_rejects_blank() -> None:
    with pytest.raises(ValueError, match="--models"):
        resolved_models("  , ")


def test_redact_database_url_masks_password() -> None:
    redacted = redact_database_url("postgresql+asyncpg://postgres:secret@localhost:5432/seal")
    assert "secret" not in redacted
    assert "postgres:secret@" not in redacted
    assert "postgres@" not in redacted
    assert "***:***@localhost:5432" in redacted


def test_redact_database_url_masks_sensitive_query_params() -> None:
    redacted = redact_database_url(
        "postgresql://localhost/seal?password=secret&api_key=abc123&sslmode=require",
    )
    assert "secret" not in redacted
    assert "abc123" not in redacted
    assert "password=%2A%2A%2A" in redacted or "password=***" in redacted
    assert "api_key=%2A%2A%2A" in redacted or "api_key=***" in redacted
    assert "sslmode=require" in redacted


def test_failed_matrix_legs_identifies_bad_run() -> None:
    matrix = {
        "comparison": True,
        "runs": [
            {
                "dialect": "postgres",
                "model": "m1",
                "database_url_redacted": "postgresql://u:***@localhost/db",
                "scored_queries": 5,
                "execution_success": 5,
                "validation_success": 5,
                "errors": [],
                "execution_rate": 1.0,
            },
            {
                "dialect": "postgres",
                "model": "m2",
                "database_url_redacted": "postgresql://u:***@localhost/db",
                "scored_queries": 5,
                "execution_success": 2,
                "validation_success": 5,
                "errors": [],
                "execution_rate": 0.4,
            },
        ],
    }
    failed = failed_matrix_legs(matrix, min_rate=0.8, planner_only=False)
    assert len(failed) == 1
    assert failed[0]["model"] == "m2"


def test_build_arg_parser_matrix_flags() -> None:
    args = build_arg_parser().parse_args(
        ["--models", "m1,m2", "--dialect-urls", "u1,u2", "--planner-only"],
    )
    assert args.models == "m1,m2"
    assert args.dialect_urls == "u1,u2"
    assert args.planner_only is True


def _eval_local_makefile_block() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    match = re.search(r"^eval-local:", makefile, re.MULTILINE)
    assert match is not None, "Makefile missing eval-local target"
    return makefile[match.start() : match.start() + 500]


def test_eval_host_db_url_matches_runner_default() -> None:
    """Makefile EVAL_HOST_DB_URL must stay in sync with DEFAULT_EVAL_DATABASE_URL."""
    repo_root = Path(__file__).resolve().parents[2]
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    needle = f"EVAL_HOST_DB_URL ?= {DEFAULT_EVAL_DATABASE_URL}"
    assert needle in makefile, f"Makefile missing: {needle}"


def test_make_eval_local_uses_make_args_not_shell() -> None:
    """eval-local must honor `make eval-local ARGS=...` (Make vars), not shell $ARGS."""
    block = _eval_local_makefile_block()
    assert "$(or $(ARGS),$(EVAL_HOST_DB_URL))" in block, (
        "eval-local recipe should use $(or $(ARGS),$(EVAL_HOST_DB_URL))"
    )
    assert "$${ARGS:-" not in block, "eval-local must not use shell ${ARGS:-...} expansion"


def test_make_eval_compare_target_exists() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    assert "eval-compare:" in makefile
    assert "--models $(MODELS)" in makefile or "--models $(MODELS)," in makefile


@pytest.mark.asyncio
async def test_load_schema_fails_fast_for_postgres() -> None:
    runner = EvalRunner("postgresql+asyncpg://localhost/seal", "postgres")
    runner.introspector = MagicMock()
    runner.introspector.introspect = AsyncMock(side_effect=RuntimeError("connection refused"))

    with pytest.raises(ConnectionError, match="Failed to introspect"):
        await runner.load_schema()


@pytest.mark.asyncio
async def test_retry_after_generate_plan_fails() -> None:
    schema = DatabaseSchema(dialect="duckdb", tables=[])
    runner = EvalRunner(":memory:", "duckdb", planner_only=True)
    runner.executor = MagicMock()
    runner.executor.close = AsyncMock()
    runner.introspector = MagicMock()
    runner.introspector.close = AsyncMock()
    runner.introspector.introspect = AsyncMock(return_value=schema)

    plan = QueryPlan(sql="SELECT 1", explanation="ok")
    generate = AsyncMock(side_effect=[RuntimeError("llm down"), plan])
    runner.planner = MagicMock()
    runner.planner.generate_plan = generate
    runner.planner.repair_plan = AsyncMock()

    valid_boundary = SqlBoundaryResult(valid=True, executable_sql="SELECT 1")
    case = {"question": "count rows", "should_fail": False}
    metrics = empty_metrics()

    with patch("seal_evals.runner.validate_and_sanitize", return_value=valid_boundary):
        await runner._evaluate_query(case, schema, metrics)

    assert generate.call_count == 2
    assert metrics["validation_success"] == 1
    assert metrics["scored_queries"] == 1
    assert metrics["errors"] == []


@pytest.mark.asyncio
async def test_validation_success_not_counted_per_failed_attempt() -> None:
    schema = DatabaseSchema(dialect="duckdb", tables=[])
    runner = EvalRunner(":memory:", "duckdb", planner_only=False)
    runner.planner = MagicMock()
    runner.planner.generate_plan = AsyncMock(
        return_value=QueryPlan(sql="SELECT 1", explanation="ok"),
    )
    runner.planner.repair_plan = AsyncMock(
        return_value=QueryPlan(sql="SELECT 1", explanation="repaired"),
    )

    valid_boundary = SqlBoundaryResult(valid=True, executable_sql="SELECT 1")
    execute = AsyncMock(side_effect=[RuntimeError("exec 1"), RuntimeError("exec 2"), None])

    metrics = empty_metrics()
    case = {"question": "revenue", "should_fail": False}

    with (
        patch("seal_evals.runner.validate_and_sanitize", return_value=valid_boundary),
        patch.object(runner.executor, "execute", execute),
    ):
        await runner._evaluate_query(case, schema, metrics)

    assert metrics["validation_success"] == 1
    assert metrics["execution_success"] == 1
    assert metrics["repair_successes"] == 2


@pytest.mark.asyncio
async def test_should_fail_expected_failure_caught() -> None:
    schema = DatabaseSchema(dialect="duckdb", tables=[])
    runner = EvalRunner(":memory:", "duckdb", planner_only=True)
    runner.planner = MagicMock()
    runner.planner.generate_plan = AsyncMock(
        return_value=QueryPlan(sql="SELECT * FROM missing_table", explanation="bad"),
    )
    runner.planner.repair_plan = AsyncMock(
        return_value=QueryPlan(sql="SELECT * FROM missing_table", explanation="still bad"),
    )

    invalid_boundary = SqlBoundaryResult(valid=False, errors=["Table missing_table does not exist"])

    metrics = empty_metrics()
    with patch("seal_evals.runner.validate_and_sanitize", return_value=invalid_boundary):
        await runner._evaluate_query(
            {"question": "from missing table", "should_fail": True},
            schema,
            metrics,
        )

    assert metrics["expected_failures_caught"] == 1
    assert metrics["validation_success"] == 0
    assert metrics["scored_queries"] == 0


@pytest.mark.asyncio
async def test_should_fail_does_not_increment_validation_success() -> None:
    schema = DatabaseSchema(dialect="duckdb", tables=[])
    runner = EvalRunner(":memory:", "duckdb", planner_only=True)
    runner.planner = MagicMock()
    runner.planner.generate_plan = AsyncMock(
        return_value=QueryPlan(sql="SELECT 1", explanation="x"),
    )

    valid_boundary = SqlBoundaryResult(valid=True, executable_sql="SELECT 1")
    metrics = empty_metrics()

    with patch("seal_evals.runner.validate_and_sanitize", return_value=valid_boundary):
        await runner._evaluate_query(
            {"question": "delete all", "should_fail": True},
            schema,
            metrics,
        )

    assert metrics["validation_success"] == 0
    assert len(metrics["errors"]) == 1


@pytest.mark.asyncio
async def test_should_fail_timeout_counts_as_expected_caught() -> None:
    schema = DatabaseSchema(dialect="duckdb", tables=[])
    runner = EvalRunner(":memory:", "duckdb", planner_only=True, query_timeout=0.01)
    runner.introspector = MagicMock()
    runner.introspector.close = AsyncMock()
    runner.introspector.introspect = AsyncMock(return_value=schema)
    runner.executor = MagicMock()
    runner.executor.close = AsyncMock()

    async def slow_eval(*_args: object, **_kwargs: object) -> None:
        await asyncio.sleep(1)

    metrics = empty_metrics()
    case = {"question": "slow negative", "should_fail": True}

    with patch.object(runner, "_evaluate_query", side_effect=slow_eval):
        await runner._run_eval_case(case, schema, metrics)

    assert metrics["timeouts"] == 1
    assert metrics["expected_failures_caught"] == 1
    assert metrics["scored_queries"] == 0
    assert metrics["errors"] == []


@pytest.mark.asyncio
async def test_run_evals_records_timeout(tmp_path: Path) -> None:
    schema = DatabaseSchema(dialect="duckdb", tables=[])
    runner = EvalRunner(":memory:", "duckdb", planner_only=True, query_timeout=0.01)
    runner.introspector = MagicMock()
    runner.introspector.close = AsyncMock()
    runner.introspector.introspect = AsyncMock(return_value=schema)
    runner.executor = MagicMock()
    runner.executor.close = AsyncMock()

    async def slow_eval(
        case: dict[str, object],
        _schema: DatabaseSchema,
        metrics: dict[str, object],
    ) -> None:
        if not case.get("should_fail"):
            metrics["scored_queries"] = int(metrics.get("scored_queries", 0)) + 1
        await asyncio.sleep(1)

    path = tmp_path / "one.jsonl"
    path.write_text('{"question": "slow", "should_fail": false}\n', encoding="utf-8")

    with patch.object(runner, "_evaluate_query", side_effect=slow_eval):
        results = await runner.run_evals(path)

    assert results["timeouts"] == 1
    assert results["error_count"] == 1
    assert results["scored_queries"] == 1


@pytest.mark.asyncio
async def test_run_evals_aborts_on_invalid_jsonl(tmp_path: Path) -> None:
    schema = DatabaseSchema(dialect="duckdb", tables=[])
    runner = EvalRunner(":memory:", "duckdb", planner_only=True)
    runner.introspector = MagicMock()
    runner.introspector.close = AsyncMock()
    runner.introspector.introspect = AsyncMock(return_value=schema)
    runner.executor = MagicMock()
    runner.executor.close = AsyncMock()

    path = tmp_path / "partial.jsonl"
    path.write_text(
        '{bad json\n{"question": "ok", "should_fail": false}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid JSON on line 1"):
        await runner.run_evals(path)

    runner.executor.close.assert_called_once()
    runner.introspector.close.assert_called_once()


def test_main_missing_eval_file() -> None:
    from seal_evals.runner import main

    exit_code = main([":memory:", "--jsonl", "/nonexistent/eval.jsonl"])
    assert exit_code == 1


def test_main_rejects_empty_models_flag() -> None:
    from seal_evals.runner import main

    exit_code = main([":memory:", "--models", "  ", "--planner-only"])
    assert exit_code == 1


@pytest.mark.asyncio
async def test_run_eval_matrix_reuses_schema_for_same_url(tmp_path: Path) -> None:
    path = tmp_path / "one.jsonl"
    path.write_text('{"question": "count rows", "should_fail": false}\n', encoding="utf-8")
    schema = DatabaseSchema(dialect="duckdb", tables=[])
    load_schema_calls = 0
    run_eval_calls = 0

    async def fake_load_schema(*_args: object, **_kwargs: object) -> DatabaseSchema:
        nonlocal load_schema_calls
        load_schema_calls += 1
        return schema

    async def fake_run_evals(
        self: EvalRunner,
        _jsonl_path: str | Path,
        *,
        schema: DatabaseSchema | None = None,
    ) -> dict[str, object]:
        nonlocal run_eval_calls
        run_eval_calls += 1
        assert schema is not None
        return summarize_metrics(
            {
                "scored_queries": 1,
                "execution_success": 1,
                "validation_success": 1,
                "errors": [],
            },
            planner_only=True,
        )

    with (
        patch("seal_evals.runner.load_schema_for_url", side_effect=fake_load_schema),
        patch.object(EvalRunner, "run_evals", fake_run_evals),
    ):
        result = await run_eval_matrix(
            database_urls=[":memory:"],
            models=["m1", "m2"],
            jsonl_path=path,
            planner_only=True,
            query_timeout=30,
        )

    assert load_schema_calls == 1
    assert run_eval_calls == 2
    assert result["comparison"] is True
    assert len(result["runs"]) == 2
    assert all("database_url_redacted" in run for run in result["runs"])
