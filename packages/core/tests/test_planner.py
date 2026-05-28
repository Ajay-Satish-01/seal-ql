from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from intelligence_core.planner.models import ChartType, QueryPlan
from intelligence_core.planner.planner import QueryPlanner
from intelligence_core.schema.models import DatabaseSchema
from pydantic import ValidationError


@pytest.fixture
def mock_schema() -> DatabaseSchema:
    return DatabaseSchema(
        dialect="postgres",
        tables=[],
        relationships=[],
        has_timescaledb=False,
    )


@pytest.fixture
def mock_query_plan() -> QueryPlan:
    return QueryPlan(
        sql="SELECT * FROM users",
        chart_type=ChartType.TABLE,
        x_field="id",
        y_field="name",
        title="All Users",
        explanation="Returns all users",
    )


@pytest.mark.asyncio
@patch("intelligence_core.planner.planner.get_async_client")
async def test_query_planner_generate_plan(
    mock_get_client: MagicMock, mock_schema: DatabaseSchema, mock_query_plan: QueryPlan
) -> None:
    # Arrange
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_query_plan
    mock_get_client.return_value = mock_client

    planner = QueryPlanner(model="test_model", api_base="test_base")

    # Act
    plan = await planner.generate_plan(mock_schema, "Show me all users")

    # Assert
    assert plan == mock_query_plan
    mock_client.chat.completions.create.assert_called_once()
    kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "test_model"
    assert kwargs["api_base"] == "test_base"
    assert kwargs["response_model"] == QueryPlan
    assert len(kwargs["messages"]) == 2
    assert kwargs["messages"][0]["role"] == "system"
    assert kwargs["messages"][1]["role"] == "user"


@pytest.mark.asyncio
@patch("intelligence_core.planner.planner.get_async_client")
async def test_query_planner_repair_plan(
    mock_get_client: MagicMock, mock_query_plan: QueryPlan
) -> None:
    # Arrange
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_query_plan
    mock_get_client.return_value = mock_client

    planner = QueryPlanner(model="test_model", api_base="test_base")

    # Act
    plan = await planner.repair_plan(
        "Show me all users", "SELECT * FROM usr", "Table 'usr' does not exist"
    )

    # Assert
    assert plan == mock_query_plan
    mock_client.chat.completions.create.assert_called_once()
    kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "test_model"
    assert kwargs["response_model"] == QueryPlan
    assert "usr" in kwargs["messages"][0]["content"]
    assert "Table 'usr' does not exist" in kwargs["messages"][0]["content"]


# ============================================================
# SQL Safety Validator Tests
# ============================================================

_VALID_PLAN_KWARGS = {
    "chart_type": ChartType.TABLE,
    "x_field": "id",
    "y_field": "name",
    "title": "Test",
    "explanation": "Test",
}


def test_sql_validator_allows_select() -> None:
    """Valid SELECT queries should pass validation."""
    plan = QueryPlan(sql="SELECT id, name FROM users", **_VALID_PLAN_KWARGS)
    assert plan.sql == "SELECT id, name FROM users"


def test_sql_validator_allows_select_with_subquery() -> None:
    plan = QueryPlan(
        sql="SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)",
        **_VALID_PLAN_KWARGS,
    )
    assert "SELECT" in plan.sql


@pytest.mark.parametrize(
    "blocked_sql",
    [
        "INSERT INTO users (name) VALUES ('evil')",
        "UPDATE users SET name = 'hacked'",
        "DELETE FROM users WHERE id = 1",
        "DROP TABLE users",
        "ALTER TABLE users ADD COLUMN evil TEXT",
        "CREATE TABLE evil (id INT)",
        "TRUNCATE TABLE users",
        "REPLACE INTO users (id, name) VALUES (1, 'evil')",
        "ATTACH DATABASE ':memory:' AS evil_db",
        "DETACH DATABASE evil_db",
        "PRAGMA table_info(users)",
        "SELECT 1; DROP TABLE users",  # multi-statement
    ],
    ids=[
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "REPLACE",
        "ATTACH",
        "DETACH",
        "PRAGMA",
        "multi-statement",
    ],
)
def test_sql_validator_blocks_destructive_patterns(blocked_sql: str) -> None:
    """Destructive SQL patterns must be rejected by the Pydantic validator."""
    with pytest.raises(ValidationError, match="blocked pattern"):
        QueryPlan(sql=blocked_sql, **_VALID_PLAN_KWARGS)
