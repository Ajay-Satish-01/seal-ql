"""API Dependency Injection."""

from fastapi import Request
from seal_core.catalog.registry import DataCatalogRegistry
from seal_core.chat.service import ChatService
from seal_core.planner.planner import QueryPlanner
from seal_core.schema.introspector import SchemaIntrospector
from seal_core.workspace.store import WorkspaceStore
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


def get_data_catalog(request: Request) -> DataCatalogRegistry:
    """Get the application's global data catalog registry."""
    return request.app.state.data_catalog


def get_chat_service(request: Request) -> ChatService:
    """Get the application's global chat service."""
    return request.app.state.chat_service


def get_workspace_store(request: Request) -> WorkspaceStore:
    """Get the application's workspace settings store."""
    return request.app.state.workspace_store
