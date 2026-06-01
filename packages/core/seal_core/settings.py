"""Centralized settings for the Seal system.

All configurable values across the project are defined here using
pydantic-settings. Values are loaded from environment variables
(and .env files), with sensible defaults for local development.

Usage:
    from seal_core.settings import get_settings

    settings = get_settings()
    print(settings.database_url)
    print(settings.resolved_llm_model)
"""

from __future__ import annotations

import logging
from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from seal_core.auth_constants import is_forbidden_api_key
from seal_core.llm_constants import (
    CLOUD_MODEL_PREFIXES,
    OLLAMA_PROFILE_DEFAULT,
    OLLAMA_PROFILE_DISABLED,
    SUPPORTED_OLLAMA_PROFILES,
)

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Global configuration for the Seal system.

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
        env_ignore_empty=True,
    )

    # ============================================================
    # Database
    # ============================================================

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/seal",
        description="Full database connection string.",
    )
    duckdb_path: str = Field(
        default=":memory:",
        description="Path to DuckDB database (or ':memory:' for in-memory).",
    )
    seal_databases_path: str | None = Field(
        default="config/databases.yaml",
        validation_alias=AliasChoices("SEAL_DATABASES_PATH", "seal_databases_path"),
        description=(
            "Optional YAML file with additional named databases for database_id routing. "
            "Missing file is ignored; DATABASE_URL always registers id 'default'."
        ),
    )
    seal_databases: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SEAL_DATABASES", "seal_databases"),
        description=(
            "Optional JSON object mapping database_id to url string or {url: ...}. "
            "Adds non-default entries; does not override DATABASE_URL default."
        ),
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
        description="LiteLLM model identifier (e.g. ollama/llama3.2:1b, gemini/gemini-2.0-flash).",
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

    @field_validator("ollama_profile", mode="before")
    @classmethod
    def _normalize_ollama_profile(cls, value: object) -> str:
        if value is None or str(value).strip() == "":
            return OLLAMA_PROFILE_DEFAULT
        return str(value).strip().lower()

    @field_validator(
        "llm_api_key",
        "gemini_api_key",
        "openai_api_key",
        "anthropic_api_key",
        mode="before",
    )
    @classmethod
    def _normalize_optional_api_keys(cls, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        text = str(value).strip()
        return text if text else None

    @field_validator(
        "data_catalog_path",
        "semantic_directory",
        "rag_documents_path",
        "seal_enhancers",
        "vector_store_class",
        "vector_store_config",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return str(value).strip() if isinstance(value, str) else str(value)

    @field_validator("vector_store", mode="before")
    @classmethod
    def _normalize_vector_store(cls, value: object) -> str:
        if value is None or str(value).strip() == "":
            return "none"
        return str(value).strip().lower()

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
        if self.use_cloud_llm() or self.is_ollama_model() or self.is_cloud_model():
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
        """Explicit API key passed to Instructor/LiteLLM in cloud mode.

        Only the generic ``LLM_API_KEY`` is returned here. Provider-specific keys
        (``GEMINI_API_KEY`` / ``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY``) are read
        directly from the environment by LiteLLM, so returning None for those is
        expected — has_cloud_api_credentials() still validates their presence.
        """
        if self.use_cloud_llm():
            return self.llm_api_key
        return None

    def llm_mode_label(self) -> str:
        return "cloud" if self.use_cloud_llm() else "ollama"

    def collect_llm_configuration_warnings(self) -> list[str]:
        """Human-readable warnings for mismatched LLM environment."""
        warnings: list[str] = []
        cloud_mode = self.use_cloud_llm()

        if self.ollama_profile not in SUPPORTED_OLLAMA_PROFILES:
            warnings.append(
                f"OLLAMA_PROFILE={self.ollama_profile!r} is not recognized. "
                f"Use {OLLAMA_PROFILE_DEFAULT!r} (local Ollama) or "
                f"{OLLAMA_PROFILE_DISABLED!r} (cloud LLM)."
            )

        if cloud_mode and self.is_ollama_model():
            warnings.append(
                f"OLLAMA_PROFILE=disabled but LLM_MODEL={self.llm_model!r} looks like Ollama. "
                "Set LLM_MODEL to a cloud id (e.g. gemini/gemini-2.0-flash)."
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

    def collect_vector_store_configuration_errors(self) -> list[str]:
        """Fatal misconfiguration for VECTOR_STORE (e.g. chroma without chromadb)."""
        from seal_core.vector.factory import chroma_is_available

        errors: list[str] = []
        if self.vector_store.lower() == "chroma" and not chroma_is_available():
            errors.append(
                "VECTOR_STORE=chroma but chromadb is not installed. "
                "Set VECTOR_STORE=none, or install seal-core[chroma] "
                "(local: uv sync --package seal-core --extra chroma; "
                "Docker: SEAL_EXTRA=chroma in .env and rebuild the api image)."
            )
        return errors

    def log_vector_store_configuration(self) -> None:
        """Log active vector backend at startup."""
        if self.vector_store_class:
            logger.info("Vector store: custom (%s)", self.vector_store_class)
        elif self.vector_store.lower() == "chroma":
            logger.info("Vector store: chroma (persist_path=%s)", self.chroma_persist_path)
        elif self.vector_store.lower() != "none":
            logger.warning("Vector store: unknown %r, will fall back to noop", self.vector_store)
        else:
            logger.info("Vector store: none (RAG disabled)")

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
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5173",
        ],
        description="Allowed CORS origins.",
    )
    api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SEAL_API_KEY", "seal_api_key"),
        description=(
            "Shared secret for API clients (sent as X-API-Key). "
            "When set, /v1/* routes require a matching key."
        ),
    )

    @field_validator("api_key", mode="before")
    @classmethod
    def _normalize_api_key(cls, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        text = str(value).strip()
        return text if text else None

    auth_required: bool = Field(
        default=False,
        validation_alias=AliasChoices("SEAL_AUTH_REQUIRED", "seal_auth_required"),
        description=(
            "When true, SEAL_API_KEY must be set at startup (no placeholder values). "
            "Runtime: /v1/* requires X-API-Key whenever SEAL_API_KEY is set, "
            "regardless of this flag."
        ),
    )
    disable_public_docs: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("SEAL_DISABLE_DOCS", "seal_disable_docs"),
        description=(
            "Hide /docs, /redoc, and /openapi.json. Defaults to the value of "
            "SEAL_AUTH_REQUIRED when unset."
        ),
    )
    dev_mode: bool = Field(
        default=False,
        validation_alias=AliasChoices("SEAL_DEV_MODE", "seal_dev_mode"),
        description=(
            "When true, allows documented placeholder API keys for local development. "
            "Must be false in production."
        ),
    )
    api_port: int = Field(
        default=8000,
        description="Port for the FastAPI server.",
    )

    def effective_disable_public_docs(self) -> bool:
        """Whether to hide /docs, /redoc, and /openapi.json."""
        if self.disable_public_docs is not None:
            return self.disable_public_docs
        return self.auth_required

    def validate_auth_configuration(self) -> list[str]:
        """Return fatal configuration errors for authentication."""
        errors: list[str] = []
        if self.auth_required and not self.api_key:
            errors.append(
                "SEAL_AUTH_REQUIRED is true but SEAL_API_KEY is not set. "
                "Generate a secret (e.g. openssl rand -hex 32) and set SEAL_API_KEY."
            )
        # auth_required is the stronger production signal: placeholders are never
        # acceptable when auth is required, even if SEAL_DEV_MODE was left on.
        if (
            self.api_key
            and is_forbidden_api_key(self.api_key)
            and (self.auth_required or not self.dev_mode)
        ):
            errors.append(
                "SEAL_API_KEY is a documented placeholder. "
                "Generate a secret (e.g. openssl rand -hex 32) or set SEAL_DEV_MODE=true "
                "(local development only, and only when SEAL_AUTH_REQUIRED is false)."
            )
        return errors

    def log_auth_configuration_warnings(self) -> None:
        """Log auth mode at startup."""
        if self.auth_required and self.api_key:
            logger.info("API authentication: required (X-API-Key)")
        elif self.api_key:
            logger.info("API authentication: enabled (X-API-Key)")
            if is_forbidden_api_key(self.api_key) and self.dev_mode:
                logger.warning(
                    "SEAL_API_KEY is a placeholder (SEAL_DEV_MODE=true). "
                    "Use a generated secret before any shared or production deployment."
                )
        else:
            logger.warning(
                "API authentication is DISABLED (SEAL_API_KEY not set). "
                "Do not expose this server to untrusted networks."
            )
        if self.effective_disable_public_docs():
            logger.info("Public API docs disabled (/docs, /redoc, /openapi.json)")
        elif self.api_key:
            logger.warning(
                "Public API docs are enabled. "
                "Set SEAL_DISABLE_DOCS=true for internet-facing deployments."
            )

    # ============================================================
    # Semantic Layer
    # ============================================================

    semantic_directory: str | None = Field(
        default=None,
        description="Path to a directory containing YAML files with semantic metrics.",
    )

    # ============================================================
    # Data catalog (auto-generated YAML)
    # ============================================================

    data_catalog_path: str | None = Field(
        default="config/catalog.yaml",
        description="Path to auto-generated data catalog YAML.",
    )
    catalog_auto_sync: bool = Field(
        default=True,
        description="Sync catalog from database schema on API startup.",
    )
    catalog_prune_removed: bool = Field(
        default=True,
        description="Remove catalog entries for relations no longer in the database.",
    )
    data_catalog_strict: bool = Field(
        default=False,
        description="Fail startup if catalog references unknown tables.",
    )
    workspace_store: str = Field(
        default="postgres",
        description=(
            "Workspace persistence: postgres (seal_app.workspace_kv, primary) with "
            "config/workspace.json read fallback; use file for file-only mode."
        ),
    )

    # ============================================================
    # Guardrails (LLM abuse / scope)
    # ============================================================

    guardrails_enabled: bool = Field(
        default=True,
        description="Enable scope classification before query/chat LLM paths.",
    )
    guardrails_fail_closed: bool = Field(
        default=True,
        description="Treat scope classification failures as out-of-scope.",
    )
    max_query_chars: int = Field(
        default=4000,
        description="Maximum characters for POST /v1/query natural language input.",
    )
    max_chat_message_chars: int = Field(
        default=8000,
        description="Maximum characters for a single chat user message.",
    )
    max_chat_history_chars: int = Field(
        default=32000,
        description="Maximum total characters for chat history override.",
    )

    # ============================================================
    # Chat / enhancement
    # ============================================================

    chat_enhancement_enabled: bool = Field(
        default=True,
        description="Enable prompt enhancement orchestrator for /v1/chat.",
    )
    strict_stream_meta_validation: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "STRICT_STREAM_META_VALIDATION",
            "STRICT_METADATA_VALIDATION",
        ),
        description=(
            "When true, invalid chat metadata (JSON) or seal.meta (SSE) payloads raise "
            "instead of only logging a warning."
        ),
    )
    chat_session_ttl_seconds: int = Field(default=3600, description="Session TTL in seconds.")
    chat_max_history_messages: int = Field(default=20, description="Max messages per session.")
    chat_summarize_after_messages: int = Field(
        default=12,
        description="Summarize conversation when history exceeds this count.",
    )
    chat_recent_messages: int = Field(
        default=6,
        description="Recent messages kept verbatim at answer stage.",
    )
    chat_answer_preview_rows: int = Field(
        default=20,
        description="Result rows fed to the LLM as grounding facts at answer stage.",
    )
    chat_max_context_tables: int = Field(
        default=8,
        description="Max tables in focused schema/catalog context.",
    )
    seal_enhancers: str | None = Field(
        default=None,
        description="Comma-separated dotted paths to extra PromptEnhancer classes.",
    )

    # ============================================================
    # Vector RAG
    # ============================================================

    vector_store: str = Field(
        default="none",
        description="Vector store backend: none, chroma, or custom via VECTOR_STORE_CLASS.",
    )
    vector_store_class: str | None = Field(
        default=None,
        description="Dotted path to custom VectorStore implementation.",
    )
    vector_store_config: str | None = Field(
        default=None,
        description="Optional JSON config for custom vector store.",
    )
    chroma_persist_path: str = Field(
        default="/app/data/chroma",
        description="Chroma persistence directory.",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="LiteLLM embedding model identifier.",
    )
    rag_documents_path: str | None = Field(
        default=None,
        description="Optional directory of documents to index for RAG.",
    )
    rag_top_k: int = Field(default=5, description="Vector search top-k.")
    rag_max_context_tokens: int = Field(default=1500, description="Max RAG text in prompt.")
    rag_embed_batch_size: int = Field(default=32, description="Embedding batch size.")
    rag_embed_max_concurrent: int = Field(default=4, description="Max concurrent embedding calls.")

    # ============================================================
    # Postgres (used by docker-compose, not directly by app code)
    # ============================================================

    postgres_user: str = Field(default="postgres", description="Postgres user.")
    postgres_password: str = Field(default="postgres", description="Postgres password.")
    postgres_db: str = Field(default="seal", description="Postgres database name.")
    postgres_port: int = Field(default=5432, description="Postgres port.")
    ollama_port: int = Field(default=11434, description="Ollama service port.")


_runtime_overrides: dict[str, object] = {}


def apply_runtime_overrides(updates: dict[str, object]) -> None:
    """Apply hot-reloaded workspace settings for the current process."""
    _runtime_overrides.update(updates)


@lru_cache(maxsize=1)
def _load_settings() -> Settings:
    return Settings()


def get_settings() -> Settings:
    """Return the global settings singleton (with optional runtime overrides)."""
    base = _load_settings()
    if _runtime_overrides:
        return base.model_copy(update=_runtime_overrides)
    return base


def clear_settings_cache() -> None:
    """Reset cached Settings and workspace runtime overrides (for tests and hot-reload)."""
    _load_settings.cache_clear()
    _runtime_overrides.clear()


def validate_llm_configuration() -> None:
    """Log LLM configuration warnings once (delegates to Settings)."""
    get_settings().log_llm_configuration_warnings()


def validate_vector_store_configuration() -> None:
    """Raise if VECTOR_STORE cannot be satisfied (e.g. chroma without chromadb)."""
    settings = get_settings()
    errors = settings.collect_vector_store_configuration_errors()
    if errors:
        raise RuntimeError("; ".join(errors))
    settings.log_vector_store_configuration()


def settings_env_names() -> list[str]:
    """Canonical uppercase environment variable names accepted by :class:`Settings`."""
    alias_overrides: dict[str, str] = {
        "api_key": "SEAL_API_KEY",
        "auth_required": "SEAL_AUTH_REQUIRED",
        "disable_public_docs": "SEAL_DISABLE_DOCS",
        "dev_mode": "SEAL_DEV_MODE",
    }
    names = {
        alias_overrides.get(field_name, field_name.upper()) for field_name in Settings.model_fields
    }
    return sorted(names)
