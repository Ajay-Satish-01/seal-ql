"""Minimal FastAPI application — expanded in Phase 6."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from intelligence_core.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — setup and teardown."""
    # TODO Phase 6: Initialize DB connection pool, LLM client, cache schema
    yield
    # TODO Phase 6: Close connections


settings = get_settings()

app = FastAPI(
    title="Intelligence Connector API",
    description="AI-powered SQL query generation, validation, and visualization",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware — origins from centralized settings.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Liveness and readiness probe."""
    return {"status": "ok"}
