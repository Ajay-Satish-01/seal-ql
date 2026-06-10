"""API Dependency Injection."""

from fastapi import Depends, Request
from seal_core.catalog.registry import DataCatalogRegistry
from seal_core.chat.service import ChatService
from seal_core.chat.session.base import BaseSessionStore
from seal_core.database.registry import DatabaseRegistry
from seal_core.pipeline.query_service import QueryService
from seal_core.planner.planner import QueryPlanner
from seal_core.reasoning.orchestrator import ReasoningOrchestrator
from seal_core.schema.introspector import SchemaIntrospector
from seal_core.workspace.store import WorkspaceStore
from seal_semantic.registry import SemanticRegistry
from seal_sql.executor import QueryExecutor


def get_database_registry(request: Request) -> DatabaseRegistry:
    """Get the application's database registry."""
    return request.app.state.database_registry


def get_schema_introspector(request: Request) -> SchemaIntrospector:
    """Get the default database schema introspector."""
    return request.app.state.database_registry.default.introspector


def get_query_planner(request: Request) -> QueryPlanner:
    """Get the application's global query planner."""
    return request.app.state.planner


def get_query_executor(request: Request) -> QueryExecutor:
    """Get the default database query executor."""
    return request.app.state.database_registry.default.executor


def get_semantic_registry(request: Request):
    """Get the application's global semantic registry."""
    return request.app.state.semantic_registry


def get_data_catalog(request: Request) -> DataCatalogRegistry:
    """Get the application's global data catalog registry."""
    return request.app.state.data_catalog


def get_reasoning_orchestrator(request: Request) -> ReasoningOrchestrator:
    """Get the application's global reasoning orchestrator."""
    return request.app.state.reasoning_orchestrator


def get_query_service(
    planner: QueryPlanner = Depends(get_query_planner),  # noqa: B008
    registry: DatabaseRegistry = Depends(get_database_registry),  # noqa: B008
    data_catalog: DataCatalogRegistry = Depends(get_data_catalog),  # noqa: B008
    semantic_registry: SemanticRegistry = Depends(get_semantic_registry),  # noqa: B008
    reasoning_orchestrator: ReasoningOrchestrator = Depends(get_reasoning_orchestrator),  # noqa: B008
) -> QueryService:
    """Build query orchestration from wired application dependencies."""
    return QueryService(
        planner=planner,
        registry=registry,
        data_catalog=data_catalog,
        semantic_registry=semantic_registry,
        reasoning_orchestrator=reasoning_orchestrator,
    )


def get_chat_service(request: Request) -> ChatService:
    """Get the application's global chat service."""
    return request.app.state.chat_service


def get_session_store(request: Request) -> BaseSessionStore:
    """Get the application's chat session store."""
    return request.app.state.session_store


def get_workspace_store(request: Request) -> WorkspaceStore:
    """Get the application's workspace settings store."""
    return request.app.state.workspace_store
