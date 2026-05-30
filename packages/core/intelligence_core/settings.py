"""Centralized settings for the intelligence_connector system.

All configurable values across the project are defined here using
pydantic-settings. Values are loaded from environment variables
(and .env files), with sensible defaults for local development.

Usage:
    from intelligence_core.settings import get_settings

    settings = get_settings()
    print(settings.database_url)
    print(settings.resolved_llm_model)
"""

from __future__ import annotations

import logging
from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from intelligence_core.llm_constants import (
    CLOUD_MODEL_PREFIXES,
    OLLAMA_PROFILE_DEFAULT,
    OLLAMA_PROFILE_DISABLED,
    SUPPORTED_OLLAMA_PROFILES,
)

logger = logging.getLogger(__name__)


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
        extra="ignore",
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
    # LLM (OLLAMA_PROFILE=disabled → cloud; default → local Ollama)
    # ============================================================

    ollama_profile: str = Field(
        default=OLLAMA_PROFILE_DEFAULT,
        description=(
            "Compose profile for Ollama: 'default' runs local Ollama; "
            "'disabled' routes LLM calls to a cloud provider."
        ),
    )
    llm_model: str = Field(
        default="ollama/llama3.2:1b",
        description="LiteLLM model identifier (e.g. ollama/llama3.2:1b, gemini/gemini-1.5-flash).",
    )
    llm_base_url: str = Field(
        default="http://ollama:11434",
        description="Ollama HTTP API (ignored when ollama_profile is disabled).",
    )
    llm_api_key: str | None = Field(
        default=None,
        description="API key passed to LiteLLM in cloud mode.",
    )
    gemini_api_key: str | None = Field(
        default=None,
        description="Gemini API key (also read by LiteLLM from the environment).",
    )
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key (also read by LiteLLM from the environment).",
    )
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key (also read by LiteLLM from the environment).",
    )
    llm_max_retries: int = Field(
        default=2,
        description="Retry attempts for LLM structured output validation.",
    )
    legacy_llm_type: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_TYPE", "llm_type"),
        description="Deprecated env var; kept only to emit a configuration warning.",
    )

    @field_validator("ollama_profile", mode="before")
    @classmethod
    def _normalize_ollama_profile(cls, value: object) -> str:
        if value is None or str(value).strip() == "":
            return OLLAMA_PROFILE_DEFAULT
        return str(value).strip().lower()

    @field_validator("legacy_llm_type", mode="before")
    @classmethod
    def _normalize_legacy_llm_type(cls, value: object) -> str | None:
        if value is None or str(value).strip() == "":
            return None
        return str(value).strip()

    def use_cloud_llm(self) -> bool:
        """True when OLLAMA_PROFILE is disabled (cloud provider, not Ollama)."""
        return self.ollama_profile == OLLAMA_PROFILE_DISABLED

    def is_cloud_model(self) -> bool:
        lower = self.llm_model.lower()
        return any(lower.startswith(prefix) for prefix in CLOUD_MODEL_PREFIXES)

    def is_ollama_model(self) -> bool:
        return self.llm_model.lower().startswith("ollama/")

    def has_cloud_api_credentials(self) -> bool:
        return bool(
            self.llm_api_key or self.gemini_api_key or self.openai_api_key or self.anthropic_api_key
        )

    @property
    def resolved_llm_model(self) -> str:
        """LiteLLM model string with ollama/ prefix applied only for bare local names."""
        # Already provider-qualified (ollama/…, gemini/…, openai/…, etc.) or cloud mode.
        if self.use_cloud_llm() or "/" in self.llm_model:
            return self.llm_model
        return f"ollama/{self.llm_model}"

    @property
    def llm_api_base(self) -> str | None:
        """API base URL for the planner; None in cloud mode."""
        if self.use_cloud_llm():
            return None
        return self.llm_base_url

    @property
    def llm_planner_api_key(self) -> str | None:
        """Explicit API key for Instructor/LiteLLM in cloud mode."""
        if self.use_cloud_llm():
            return self.llm_api_key
        return None

    def llm_mode_label(self) -> str:
        return "cloud" if self.use_cloud_llm() else "ollama"

    def collect_llm_configuration_warnings(self) -> list[str]:
        """Human-readable warnings for mismatched LLM environment."""
        warnings: list[str] = []
        cloud_mode = self.use_cloud_llm()

        if self.legacy_llm_type:
            warnings.append(
                f"LLM_TYPE={self.legacy_llm_type!r} is no longer used. "
                f"Set OLLAMA_PROFILE={OLLAMA_PROFILE_DISABLED!r}, a cloud LLM_MODEL "
                "(e.g. gemini/…), and LLM_API_KEY or a provider API key."
            )

        if self.ollama_profile not in SUPPORTED_OLLAMA_PROFILES:
            warnings.append(
                f"OLLAMA_PROFILE={self.ollama_profile!r} is not recognized. "
                f"Use {OLLAMA_PROFILE_DEFAULT!r} (local Ollama) or "
                f"{OLLAMA_PROFILE_DISABLED!r} (cloud LLM)."
            )

        if cloud_mode and self.is_ollama_model():
            warnings.append(
                f"OLLAMA_PROFILE=disabled but LLM_MODEL={self.llm_model!r} looks like Ollama. "
                "Set LLM_MODEL to a cloud id (e.g. gemini/gemini-1.5-flash)."
            )

        if not cloud_mode and self.is_cloud_model():
            warnings.append(
                f"LLM_MODEL={self.llm_model!r} looks like a cloud provider, but "
                f"OLLAMA_PROFILE is {self.ollama_profile!r}. "
                f"Set OLLAMA_PROFILE={OLLAMA_PROFILE_DISABLED!r} and an API key."
            )

        if not cloud_mode and not self.is_ollama_model() and not self.is_cloud_model():
            warnings.append(
                f"LLM_MODEL={self.llm_model!r} has no ollama/ or known cloud prefix. "
                f"Use ollama/model:tag locally or OLLAMA_PROFILE="
                f"{OLLAMA_PROFILE_DISABLED!r} for cloud."
            )

        if cloud_mode and not self.is_cloud_model() and not self.is_ollama_model():
            warnings.append(
                f"OLLAMA_PROFILE=disabled with LLM_MODEL={self.llm_model!r}. "
                "Use a provider prefix (gemini/, openai/, anthropic/, …)."
            )

        if cloud_mode and not self.has_cloud_api_credentials():
            warnings.append(
                "OLLAMA_PROFILE=disabled but no API key found. Set LLM_API_KEY or "
                "GEMINI_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY."
            )

        return warnings

    def log_llm_configuration_warnings(self) -> None:
        for message in self.collect_llm_configuration_warnings():
            logger.warning("LLM configuration: %s", message)

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
    ollama_port: int = Field(default=11434, description="Ollama service port.")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the global settings singleton."""
    return Settings()


def validate_llm_configuration() -> None:
    """Log LLM configuration warnings once (delegates to Settings)."""
    get_settings().log_llm_configuration_warnings()
