"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from intelligence_core.planner.planner import QueryPlanner
from intelligence_core.schema.introspector import get_introspector
from intelligence_core.settings import get_settings
from intelligence_sql.executor import QueryExecutor

from app.routes import health, query, schema

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application."""
    settings = get_settings()

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

    # Store on app state
    app.state.introspector = introspector
    app.state.executor = executor
    app.state.planner = planner

    yield

    # Teardown
    logger.info("Closing database connections...")
    await executor.close()
    await introspector.close()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Intelligence Connector API",
        version="0.1.0",
        description="AI-powered SQL generation and execution.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    app.include_router(health.router)
    app.include_router(schema.router, prefix="/v1")
    app.include_router(query.router, prefix="/v1")

    return app


app = create_app()
