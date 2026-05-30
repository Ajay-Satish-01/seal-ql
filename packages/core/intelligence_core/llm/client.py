"""LLM client wrapper — thin layer over LiteLLM + Instructor.

All runtime configuration is read from :class:`intelligence_core.settings.Settings`.
"""

from __future__ import annotations

import instructor
from litellm import acompletion

from intelligence_core.settings import get_settings, validate_llm_configuration

_config_validated = False


def get_async_client() -> instructor.AsyncInstructor:
    """Returns an instructor-patched LiteLLM async client."""
    return instructor.from_litellm(acompletion)


def validate_llm_env() -> None:
    """Log LLM configuration warnings once per process."""
    global _config_validated
    if _config_validated:
        return
    _config_validated = True
    validate_llm_configuration()


def get_model() -> str:
    return get_settings().resolved_llm_model


def get_api_base() -> str | None:
    return get_settings().llm_api_base


def get_api_key() -> str | None:
    return get_settings().llm_planner_api_key
