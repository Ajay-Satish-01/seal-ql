"""LLM client wrapper — thin layer over LiteLLM + Instructor.

All configuration comes from the centralized Settings class.
No os.getenv() calls here — that's handled by pydantic-settings.
"""

from __future__ import annotations

import instructor
from litellm import acompletion

from intelligence_core.settings import get_settings


def get_async_client() -> instructor.AsyncInstructor:
    """Returns an instructor-patched LiteLLM async client.

    This client is capable of generating structured output (Pydantic models)
    using the litellm abstraction over any LLM provider.
    """
    return instructor.from_litellm(acompletion)


def get_model() -> str:
    """Returns the configured LLM model string.

    Reads from ``LLM_MODEL`` env var via Settings.
    Defaults to ``ollama/llama3.2:3b`` for local, zero-cost execution.
    """
    return get_settings().llm_model


def get_api_base() -> str:
    """Returns the configured API base URL for the LLM.

    Reads from ``LLM_BASE_URL`` env var via Settings.
    Defaults to the local Ollama instance.
    """
    return get_settings().llm_base_url
