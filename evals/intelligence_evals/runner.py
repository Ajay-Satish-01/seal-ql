import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from intelligence_core.planner.planner import QueryPlanner
from intelligence_core.schema.introspector import get_introspector
from intelligence_core.schema.models import DatabaseSchema
from intelligence_sql.executor import QueryExecutor
from intelligence_sql.sanitizer import SQLSanitizer
from intelligence_sql.validator import SQLValidator

logger = logging.getLogger(__name__)


class EvalRunner:
    def __init__(self, db_url: str, dialect: str):
        self.db_url = db_url
        self.dialect = dialect
        self.planner = QueryPlanner()
        self.executor = QueryExecutor(dialect, db_url)
        self.introspector = get_introspector(dialect, db_url)

    async def run_evals(self, jsonl_path: str | Path) -> dict[str, Any]:
        path = Path(jsonl_path)
        if not path.exists():
            raise FileNotFoundError(f"Eval set not found at {path}")

        logger.info(f"Introspecting schema from {self.db_url}...")
        try:
            schema = await self.introspector.introspect()
        except Exception as e:
            logger.error(f"Failed to introspect schema: {e}")
            # Mock schema for test cases where DB isn't available
            schema = DatabaseSchema(dialect=self.dialect, tables=[])

        metrics = {
            "total_queries": 0,
            "execution_success": 0,
            "validation_success": 0,
            "expected_failures_caught": 0,
            "repair_successes": 0,
            "errors": [],
        }

        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                metrics["total_queries"] += 1
                await self._evaluate_query(data, schema, metrics)

        await self.executor.close()
        await self.introspector.close()
        return metrics

    async def _evaluate_query(self, data: dict, schema: DatabaseSchema, metrics: dict):
        question = data.get("question", "")
        should_fail = data.get("should_fail", False)

        logger.info(f"Evaluating query: {question}")

        max_attempts = 3
        current_attempt = 1
        plan = None

        while current_attempt <= max_attempts:
            try:
                if current_attempt == 1:
                    plan = await self.planner.generate_plan(schema, question)

                # Validation
                validator = SQLValidator(schema)
                val_result = validator.validate(plan.sql)
                if not val_result.valid:
                    raise ValueError(f"Validation failed: {val_result.errors}")

                metrics["validation_success"] += 1

                # Sanitization
                sanitizer = SQLSanitizer()
                san_result = sanitizer.sanitize(val_result.normalized_sql)
                if not san_result.safe:
                    raise ValueError("Sanitization failed")

                # Execution
                # Note: This might fail if the DB doesn't match the schema/query perfectly
                # In real evals, we'd have a seeded DB.
                try:
                    await self.executor.execute(san_result.sanitized_sql)
                    metrics["execution_success"] += 1

                    if should_fail:
                        metrics["errors"].append(
                            f"Query '{question}' was expected to fail but succeeded."
                        )
                    break  # Success

                except Exception as exec_err:
                    raise ValueError(f"Execution failed: {exec_err}") from exec_err

            except Exception as e:
                if current_attempt >= max_attempts:
                    if should_fail:
                        metrics["expected_failures_caught"] += 1
                    else:
                        metrics["errors"].append(
                            f"Query '{question}' failed after {max_attempts} attempts: {str(e)}"
                        )
                    break

                # Attempt Repair
                if plan:
                    plan = await self.planner.repair_plan(question, plan.sql, str(e))
                metrics["repair_successes"] += 1  # Rough metric
                current_attempt += 1


if __name__ == "__main__":
    import sys

    async def main():
        logging.basicConfig(level=logging.INFO)
        # Check if URL passed, else use DuckDB in memory
        db_url = sys.argv[1] if len(sys.argv) > 1 else ":memory:"
        dialect = "postgres" if "postgres" in db_url else "duckdb"

        runner = EvalRunner(db_url, dialect)
        eval_path = Path(__file__).parent.parent / "data" / "eval_set.jsonl"

        results = await runner.run_evals(eval_path)
        print("\n=== Eval Results ===")
        print(json.dumps(results, indent=2))

    asyncio.run(main())
