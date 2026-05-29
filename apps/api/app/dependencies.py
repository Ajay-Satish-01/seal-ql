"""API Dependency Injection."""

from fastapi import Request
from intelligence_core.planner.planner import QueryPlanner
from intelligence_core.schema.introspector import SchemaIntrospector
from intelligence_sql.executor import QueryExecutor


def get_schema_introspector(request: Request) -> SchemaIntrospector:
    """Get the application's global schema introspector."""
    return request.app.state.introspector


def get_query_planner(request: Request) -> QueryPlanner:
    """Get the application's global query planner."""
    return request.app.state.planner


def get_query_executor(request: Request) -> QueryExecutor:
    """Get the application's global query executor."""
    return request.app.state.executor
