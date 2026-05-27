"""Minimal FastAPI application — expanded in Phase 6."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — setup and teardown."""
    # TODO Phase 6: Initialize DB connection pool, LLM client, cache schema
    yield
    # TODO Phase 6: Close connections


app = FastAPI(
    title="Intelligence Connector API",
    description="AI-powered SQL query generation, validation, and visualization",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Liveness and readiness probe."""
    return {"status": "ok"}
