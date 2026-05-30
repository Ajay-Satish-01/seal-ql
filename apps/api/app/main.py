"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from seal_core.llm.client import validate_llm_env
from seal_core.planner.planner import QueryPlanner
from seal_core.schema.introspector import get_introspector
from seal_core.settings import get_settings
from seal_semantic.registry import SemanticRegistry
from seal_sql.executor import QueryExecutor

from app.routes import health, query, schema

# Load .env into os.environ so litellm can find provider-specific keys (e.g. GEMINI_API_KEY)
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

    # Extract dialect from database url (e.g. postgresql:// -> postgres)
    dialect = "postgres" if "postgres" in settings.database_url else "duckdb"

    # 1. Initialize Schema Introspector
    logger.info(f"Initializing Schema Introspector for dialect: {dialect}")
    introspector = get_introspector(dialect, settings.database_url)

    # 2. Initialize Query Executor (has internal connection pool)
    logger.info("Initializing Query Executor")
    executor = QueryExecutor(dialect, settings.database_url)

    # 3. Initialize Query Planner
    logger.info("Initializing Query Planner")
    planner = QueryPlanner()

    # 4. Initialize Semantic Registry
    logger.info("Initializing Semantic Registry")
    semantic_registry = SemanticRegistry(settings.semantic_directory)

    # Store on app state
    app.state.introspector = introspector
    app.state.executor = executor
    app.state.planner = planner
    app.state.semantic_registry = semantic_registry

    yield

    # Teardown
    logger.info("Closing database connections...")
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
        description="AI-powered SQL generation and execution.",
        lifespan=lifespan,
        **docs_kwargs,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )

    # Mount routers
    app.include_router(health.router)
    app.include_router(schema.router, prefix="/v1")
    app.include_router(query.router, prefix="/v1")

    return app


app = create_app()
