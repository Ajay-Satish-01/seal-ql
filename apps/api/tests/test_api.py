from app.dependencies import get_query_executor, get_query_planner, get_schema_introspector
from app.main import app
from fastapi.testclient import TestClient
from intelligence_core.planner.models import ChartType, QueryPlan
from intelligence_core.schema.models import DatabaseSchema
from intelligence_sql.result import ColumnMetadata, QueryResult

# --- Mocks ---


class MockIntrospector:
    async def introspect(self):
        return DatabaseSchema(tables=[], dialect="postgres")


class MockPlanner:
    async def plan(self, query: str, schema: DatabaseSchema):
        return QueryPlan(
            sql="SELECT 1 as id",
            chart_type=ChartType.TABLE,
            x_field="id",
            y_field="id",
            title="Test",
            explanation="Test query",
        )


class MockExecutor:
    async def execute(self, sql: str):
        return QueryResult(
            columns=[ColumnMetadata("id", "int")],
            rows=[{"id": 1}],
            row_count=1,
            execution_time_ms=1.0,
            truncated=False,
            sql=sql,
        )


# --- Overrides ---

app.dependency_overrides[get_schema_introspector] = lambda: MockIntrospector()
app.dependency_overrides[get_query_planner] = lambda: MockPlanner()
app.dependency_overrides[get_query_executor] = lambda: MockExecutor()

client = TestClient(app)

# --- Tests ---


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_schema():
    response = client.get("/v1/schema")
    assert response.status_code == 200
    assert "tables" in response.json()


def test_query():
    response = client.post("/v1/query", json={"query": "test query"})
    assert response.status_code == 200
    data = response.json()
    assert "sql" in data
    assert data["sql"] == "SELECT 1 AS id LIMIT 10000"  # Sanitizer injects LIMIT
    assert len(data["results"]) == 1
    assert data["results"][0]["id"] == 1
