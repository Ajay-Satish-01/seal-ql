"""Centralized settings for the intelligence_connector system.

All configurable values across the project are defined here using
pydantic-settings. Values are loaded from environment variables
(and .env files), with sensible defaults for local development.

Usage:
    from intelligence_core.settings import get_settings

    settings = get_settings()
    print(settings.database_url)
    print(settings.query_timeout_seconds)
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration for the intelligence_connector system.

    Reads from environment variables (case-insensitive). Supports `.env` files
    for local development.

    All packages (core, sql, charts, semantic, api) import this single class
    instead of defining their own defaults or calling os.getenv() directly.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Allow extra fields from .env that we don't model (e.g., POSTGRES_USER).
        extra="ignore",
        # Case-insensitive env var matching.
        case_sensitive=False,
    )

    # ============================================================
    # Database
    # ============================================================

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/intelligence_connector",
        description="Full database connection string.",
    )
    duckdb_path: str = Field(
        default=":memory:",
        description="Path to DuckDB database (or ':memory:' for in-memory).",
    )

    # ============================================================
    # LLM
    # ============================================================

    llm_type: str = Field(
        default="local",
        description="Type of LLM ('local' for ollama, 'cloud' for external providers).",
    )
    llm_model: str = Field(
        default="ollama/llama3.2:1b",
        description="LiteLLM model identifier (e.g., 'ollama/llama3.1', 'gpt-4o-mini').",
    )
    llm_base_url: str = Field(
        default="http://ollama:11434",
        description="Base URL for the LLM API.",
    )
    llm_api_key: str | None = Field(
        default=None,
        description="API key for the LLM provider (not needed for Ollama).",
    )
    llm_max_retries: int = Field(
        default=2,
        description="Number of retry attempts for LLM structured output validation.",
    )

    # ============================================================
    # Query Safety — Sanitizer
    # ============================================================

    max_rows: int = Field(
        default=10_000,
        description="Maximum rows the sanitizer allows (LIMIT injection/clamping).",
    )
    max_joins: int = Field(
        default=10,
        description="Maximum JOIN clauses allowed in a query.",
    )
    max_subquery_depth: int = Field(
        default=5,
        description="Maximum nesting depth of subqueries.",
    )

    # ============================================================
    # Query Safety — Executor
    # ============================================================

    query_timeout_seconds: float = Field(
        default=30.0,
        description="Maximum seconds to wait for a query to complete.",
    )
    query_max_retries: int = Field(
        default=2,
        description="Number of retry attempts for transient query failures.",
    )
    query_row_cap: int = Field(
        default=10_000,
        description="Executor-level row cap safety net.",
    )
    query_retry_base_delay: float = Field(
        default=0.5,
        description="Base delay in seconds for exponential backoff on retries.",
    )

    # ============================================================
    # API / Server
    # ============================================================

    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins.",
    )
    api_port: int = Field(
        default=8000,
        description="Port for the FastAPI server.",
    )

    # ============================================================
    # Semantic Layer
    # ============================================================

    semantic_directory: str | None = Field(
        default=None,
        description="Path to a directory containing YAML files with semantic metrics.",
    )

    # ============================================================
    # Postgres (used by docker-compose, not directly by app code)
    # ============================================================

    postgres_user: str = Field(default="postgres", description="Postgres user.")
    postgres_password: str = Field(default="postgres", description="Postgres password.")
    postgres_db: str = Field(
        default="intelligence_connector", description="Postgres database name."
    )
    postgres_port: int = Field(default=5432, description="Postgres port.")

    # ============================================================
    # Ollama (used by docker-compose)
    # ============================================================

    ollama_port: int = Field(default=11434, description="Ollama service port.")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the global settings singleton.

    Uses ``lru_cache`` so the settings are loaded and validated once,
    then reused for the lifetime of the process.

    To override in tests, use ``get_settings.cache_clear()`` after
    monkey-patching environment variables.

    Returns:
        The loaded Settings instance.
    """
    return Settings()
