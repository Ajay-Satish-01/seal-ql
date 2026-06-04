"""Map LiteLLM failures to safe HTTP status codes and client-facing messages."""

from __future__ import annotations

import litellm

_CLIENT_LLM_AUTH = (
    "LLM authentication failed. Check LLM_API_KEY or provider API keys "
    "(GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY) in .env."
)
_CLIENT_LLM_MODEL = (
    "LLM model not found or unavailable. Update LLM_MODEL in .env or workspace settings."
)
_CLIENT_LLM_MODEL_DECOMMISSIONED = (
    "LLM model is decommissioned or no longer supported by the provider. "
    "Update LLM_MODEL in .env or workspace settings."
)
_CLIENT_LLM_BAD_REQUEST = (
    "LLM request rejected by the provider (invalid model or parameters). "
    "Check LLM_MODEL and provider documentation."
)
_CLIENT_LLM_RATE = "LLM rate limit exceeded. Retry later or switch models."
_CLIENT_LLM_GENERIC = "LLM request failed. See server logs for details."

_LITELLM_EXCEPTION_TYPES = (
    litellm.AuthenticationError,
    litellm.NotFoundError,
    litellm.BadRequestError,
    litellm.RateLimitError,
    litellm.APIError,
    litellm.InternalServerError,
)


def _looks_like_missing_credentials(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "missing credentials" in text or (
        "api_key" in text and ("environment variable" in text or "please pass" in text)
    )


def _walk_exception_chain(exc: BaseException) -> list[BaseException]:
    visited: set[int] = set()
    chain: list[BaseException] = []
    stack: list[BaseException] = [exc]
    while stack:
        current = stack.pop()
        marker = id(current)
        if marker in visited:
            continue
        visited.add(marker)
        chain.append(current)
        if current.__cause__ is not None:
            stack.append(current.__cause__)
        context = current.__context__
        if context is not None and context is not current.__cause__:
            stack.append(context)
    return chain


def find_litellm_exception(exc: BaseException) -> BaseException | None:
    """Walk exception causes and return the first LiteLLM error, if any."""
    visited: set[int] = set()
    stack: list[BaseException] = [exc]
    while stack:
        current = stack.pop()
        marker = id(current)
        if marker in visited:
            continue
        visited.add(marker)
        if isinstance(current, _LITELLM_EXCEPTION_TYPES):
            return current
        if current.__cause__ is not None:
            stack.append(current.__cause__)
        context = current.__context__
        if context is not None and context is not current.__cause__:
            stack.append(context)
    return None


def _bad_request_client_message(exc: BaseException) -> str:
    """Map provider 400-style LiteLLM errors to a safe client message."""
    text = str(exc).lower()
    if "decommissioned" in text or "model_decommissioned" in text:
        return _CLIENT_LLM_MODEL_DECOMMISSIONED
    if "not found" in text and "model" in text:
        return _CLIENT_LLM_MODEL
    return _CLIENT_LLM_BAD_REQUEST


def llm_http_error(exc: BaseException) -> tuple[int, str] | None:
    """Return ``(status_code, detail)`` for known LLM failures, else ``None``."""
    for link in _walk_exception_chain(exc):
        if _looks_like_missing_credentials(link):
            return 502, _CLIENT_LLM_AUTH

    root = find_litellm_exception(exc)
    if root is None:
        return None
    if isinstance(root, litellm.AuthenticationError):
        return 502, _CLIENT_LLM_AUTH
    if isinstance(root, litellm.NotFoundError):
        return 502, _CLIENT_LLM_MODEL
    if isinstance(root, litellm.BadRequestError):
        return 502, _bad_request_client_message(root)
    if isinstance(root, litellm.RateLimitError):
        return 503, _CLIENT_LLM_RATE
    if isinstance(root, litellm.APIError):
        return 502, _CLIENT_LLM_GENERIC
    return None
