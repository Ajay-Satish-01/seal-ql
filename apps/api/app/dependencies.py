"""API Dependency Injection."""

from fastapi import Request
from seal_core.planner.planner import QueryPlanner
from seal_core.schema.introspector import SchemaIntrospector
from seal_sql.executor import QueryExecutor


def get_schema_introspector(request: Request) -> SchemaIntrospector:
    """Get the application's global schema introspector."""
    return request.app.state.introspector


def get_query_planner(request: Request) -> QueryPlanner:
    """Get the application's global query planner."""
    return request.app.state.planner


def get_query_executor(request: Request) -> QueryExecutor:
    """Get the application's global query executor."""
    return request.app.state.executor


def get_semantic_registry(request: Request):
    """Get the application's global semantic registry."""
    return request.app.state.semantic_registry
