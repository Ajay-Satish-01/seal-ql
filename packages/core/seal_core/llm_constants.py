"""Shared LLM configuration constants (used by Settings only)."""

from __future__ import annotations

OLLAMA_PROFILE_DEFAULT = "default"
OLLAMA_PROFILE_DISABLED = "disabled"
SUPPORTED_OLLAMA_PROFILES = frozenset({OLLAMA_PROFILE_DEFAULT, OLLAMA_PROFILE_DISABLED})

CLOUD_MODEL_PREFIXES = (
    "gemini/",
    "openai/",
    "anthropic/",
    "azure/",
    "vertex_ai/",
    "cohere/",
    "mistral/",
    "deepseek/",
    "xai/",
)
