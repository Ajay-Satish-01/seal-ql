"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from seal_core.catalog.registry import DataCatalogRegistry
from seal_core.catalog.sync import sync_catalog
from seal_core.chat.service import ChatService
from seal_core.chat.sessions import SessionStore
from seal_core.enhancement.orchestrator import build_default_orchestrator
from seal_core.llm.client import validate_llm_env
from seal_core.planner.planner import QueryPlanner
from seal_core.schema.introspector import get_introspector
from seal_core.settings import get_settings, validate_vector_store_configuration
from seal_core.vector.factory import get_vector_store
from seal_core.vector.indexer import VectorIndexBuilder
from seal_core.workspace.bootstrap import apply_workspace_on_startup
from seal_core.workspace.store import create_workspace_store
from seal_semantic.registry import SemanticRegistry
from seal_sql.executor import QueryExecutor

from app.routes import catalog, chat, health, query, schema, vector, workspace

load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application."""
    settings = get_settings()
    logger.info(
        "LLM mode: %s (model=%s, ollama_profile=%s)",
        settings.llm_mode_label(),
        settings.resolved_llm_model,
        settings.ollama_profile,
    )
    validate_llm_env()

    auth_errors = settings.validate_auth_configuration()
    if auth_errors:
        for message in auth_errors:
            logger.error(message)
        raise RuntimeError("; ".join(auth_errors))
    settings.log_auth_configuration_warnings()
    validate_vector_store_configuration()

    dialect = "postgres" if "postgres" in settings.database_url else "duckdb"

    logger.info("Initializing Schema Introspector for dialect: %s", dialect)
    introspector = get_introspector(dialect, settings.database_url)

    logger.info("Initializing Query Executor")
    executor = QueryExecutor(dialect, settings.database_url)

    logger.info("Initializing Query Planner")
    planner = QueryPlanner()

    logger.info("Initializing Semantic Registry")
    semantic_registry = SemanticRegistry(settings.semantic_directory)

    data_catalog = DataCatalogRegistry()
    if settings.data_catalog_path:
        catalog_path = Path(settings.data_catalog_path)
        if settings.catalog_auto_sync:
            schema = await introspector.introspect()
            await sync_catalog(
                schema,
                catalog_path,
                prune_removed=settings.catalog_prune_removed,
            )
        data_catalog.load(catalog_path)
        if settings.data_catalog_strict:
            schema = await introspector.introspect()
            errors = data_catalog.validate_against_schema(schema)
            if errors:
                raise RuntimeError("; ".join(errors))

    vector_store = get_vector_store(settings)
    if settings.vector_store.lower() != "none" or settings.vector_store_class:
        try:
            schema = await introspector.introspect()
            builder = VectorIndexBuilder(vector_store)
            await builder.build(schema, data_catalog)
        except Exception as e:
            logger.warning("Vector index build skipped: %s", e)

    orchestrator = None
    if settings.chat_enhancement_enabled:
        orchestrator = build_default_orchestrator(
            catalog=data_catalog,
            semantic_registry=semantic_registry,
            vector_store=vector_store,
        )

    chat_service = ChatService(
        planner=planner,
        executor=executor,
        sessions=SessionStore(),
        orchestrator=orchestrator,
        catalog=data_catalog,
        semantic_registry=semantic_registry,
    )

    app.state.introspector = introspector
    app.state.executor = executor
    app.state.planner = planner
    app.state.semantic_registry = semantic_registry
    app.state.data_catalog = data_catalog
    app.state.chat_service = chat_service
    app.state.vector_store = vector_store
    workspace_store = create_workspace_store()
    app.state.workspace_store = workspace_store
    if hasattr(workspace_store, "ensure_schema"):
        await workspace_store.ensure_schema()
    await apply_workspace_on_startup(workspace_store, data_catalog)

    yield

    logger.info("Closing database connections...")
    await workspace_store.close()
    await executor.close()
    await introspector.close()


def create_app() -> FastAPI:
    settings = get_settings()

    docs_kwargs: dict[str, str | None] = {}
    if settings.effective_disable_public_docs():
        docs_kwargs = {
            "docs_url": None,
            "redoc_url": None,
            "openapi_url": None,
        }

    app = FastAPI(
        title="Seal API",
        version="0.1.0",
        description="AI-powered SQL generation, chat Q&A, and visualization.",
        lifespan=lifespan,
        **docs_kwargs,
    )

    # Never combine a wildcard origin with credentials: that lets any site make
    # credentialed cross-origin calls. When origins are wildcarded, drop
    # credentials (Starlette would otherwise echo "*" and browsers reject it).
    cors_origins = settings.cors_origins
    allow_credentials = "*" not in cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )

    app.include_router(health.router)
    app.include_router(schema.router, prefix="/v1")
    app.include_router(query.router, prefix="/v1")
    app.include_router(chat.router, prefix="/v1")
    app.include_router(catalog.router, prefix="/v1")
    app.include_router(workspace.router, prefix="/v1")
    app.include_router(vector.router, prefix="/v1")

    return app


app = create_app()
