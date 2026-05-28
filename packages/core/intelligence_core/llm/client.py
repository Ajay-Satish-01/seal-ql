import os

import instructor
from litellm import acompletion


def get_async_client() -> instructor.AsyncInstructor:
    """
    Returns an instructor-patched LiteLLM async client.
    This client is capable of generating structured output (Pydantic models)
    using the litellm abstraction over any LLM provider.
    """
    return instructor.from_litellm(acompletion)


def get_model() -> str:
    """
    Returns the configured LLM model string.
    Defaults to ollama/llama3.1 for local, zero-cost execution.
    """
    return os.getenv("LLM_MODEL", "ollama/llama3.2:3b")


def get_api_base() -> str:
    """
    Returns the configured API base URL for the LLM.
    Defaults to the local Ollama instance.
    """
    return os.getenv("LLM_BASE_URL", "http://localhost:11434")
