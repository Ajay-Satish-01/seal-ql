"""Workspace settings field metadata for dashboard and API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class SettingField:
    key: str
    env_name: str
    hot_reload: bool
    value_type: Literal["bool", "int", "str"]
    description: str
    default: Any
    secret: bool = False


def settings_schema() -> list[SettingField]:
    """Canonical workspace-tunable settings (subset of Settings)."""
    return [
        SettingField(
            key="guardrails_enabled",
            env_name="GUARDRAILS_ENABLED",
            hot_reload=True,
            value_type="bool",
            description="Enable scope classification for query and chat.",
            default=True,
        ),
        SettingField(
            key="guardrails_fail_closed",
            env_name="GUARDRAILS_FAIL_CLOSED",
            hot_reload=True,
            value_type="bool",
            description="Treat scope classifier failures as out-of-scope.",
            default=True,
        ),
        SettingField(
            key="max_query_chars",
            env_name="MAX_QUERY_CHARS",
            hot_reload=True,
            value_type="int",
            description="Max characters for /v1/query input.",
            default=4000,
        ),
        SettingField(
            key="max_chat_message_chars",
            env_name="MAX_CHAT_MESSAGE_CHARS",
            hot_reload=True,
            value_type="int",
            description="Max characters per chat user message.",
            default=8000,
        ),
        SettingField(
            key="max_chat_history_chars",
            env_name="MAX_CHAT_HISTORY_CHARS",
            hot_reload=True,
            value_type="int",
            description="Max total characters in chat history override.",
            default=32000,
        ),
        SettingField(
            key="chat_enhancement_enabled",
            env_name="CHAT_ENHANCEMENT_ENABLED",
            hot_reload=True,
            value_type="bool",
            description="Enable prompt enhancement on /v1/chat.",
            default=True,
        ),
        SettingField(
            key="vector_store",
            env_name="VECTOR_STORE",
            hot_reload=False,
            value_type="str",
            description="Vector backend: none or chroma.",
            default="none",
        ),
        SettingField(
            key="cors_origins",
            env_name="CORS_ORIGINS",
            hot_reload=False,
            value_type="str",
            description="Comma-separated allowed CORS origins (restart required).",
            default="http://localhost:3000,http://localhost:3001",
        ),
        SettingField(
            key="llm_model",
            env_name="LLM_MODEL",
            hot_reload=True,
            value_type="str",
            description="LiteLLM model identifier (e.g. ollama/llama3.2:1b).",
            default="ollama/llama3.2:1b",
        ),
        SettingField(
            key="max_rows",
            env_name="MAX_ROWS",
            hot_reload=True,
            value_type="int",
            description="Maximum rows allowed by the SQL sanitizer.",
            default=10_000,
        ),
        SettingField(
            key="chat_max_context_tables",
            env_name="CHAT_MAX_CONTEXT_TABLES",
            hot_reload=True,
            value_type="int",
            description="Max tables in focused chat schema context.",
            default=8,
        ),
        SettingField(
            key="embedding_model",
            env_name="EMBEDDING_MODEL",
            hot_reload=False,
            value_type="str",
            description="LiteLLM embedding model (reindex vector store after change).",
            default="text-embedding-3-small",
        ),
        SettingField(
            key="rag_top_k",
            env_name="RAG_TOP_K",
            hot_reload=True,
            value_type="int",
            description="Vector search top-k for RAG enhancement.",
            default=5,
        ),
    ]


def schema_by_key() -> dict[str, SettingField]:
    return {f.key: f for f in settings_schema()}
