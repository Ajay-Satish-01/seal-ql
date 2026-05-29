"""LLM client wrapper — thin layer over LiteLLM + Instructor.

All configuration comes from the centralized Settings class.
No os.getenv() calls here — that's handled by pydantic-settings.
"""

from __future__ import annotations

import logging

import instructor
from litellm import acompletion, validate_environment

from intelligence_core.settings import get_settings

logger = logging.getLogger(__name__)


def get_async_client() -> instructor.AsyncInstructor:
    """Returns an instructor-patched LiteLLM async client."""
    return instructor.from_litellm(acompletion)


def validate_llm_env() -> None:
    """Validates the environment for the configured LLM model."""
    settings = get_settings()
    if settings.llm_type.lower() == "cloud":
        missing = validate_environment(settings.llm_model)
        if missing and not missing.get("keys_in_environment"):
            logger.warning(
                f"Missing environment variables for {settings.llm_model}: "
                f"{missing.get('missing_keys')}"
            )


def get_model() -> str:
    """Returns the configured LLM model string."""
    settings = get_settings()
    model = settings.llm_model
    if settings.llm_type.lower() != "cloud" and not model.startswith("ollama/"):
        return f"ollama/{model}"
    return model


def get_api_base() -> str | None:
    """Returns the configured API base URL for the LLM if applicable."""
    settings = get_settings()
    if settings.llm_type.lower() != "cloud":
        return settings.llm_base_url
    return None


def get_api_key() -> str | None:
    """Returns the configured API key for the LLM if applicable."""
    settings = get_settings()
    if settings.llm_type.lower() == "cloud":
        return settings.llm_api_key
    return None
