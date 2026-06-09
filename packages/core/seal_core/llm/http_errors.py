"""Map LiteLLM failures to safe HTTP status codes and client-facing messages."""

from __future__ import annotations

import litellm

from seal_core.llm.rate_limit import (
    is_rate_limit_http,
    looks_like_rate_limit_text,
    rate_limit_user_message,
)

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


def _is_rate_limit_mapping(mapped: tuple[int, str]) -> bool:
    status, detail = mapped
    return status == 503 and detail == rate_limit_user_message()


def llm_error_event_code(mapped: tuple[int, str] | None) -> str:
    """SSE ``seal.error`` code for a mapped LiteLLM failure."""
    if mapped is None:
        return "error"
    if _is_rate_limit_mapping(mapped):
        return "rate_limit"
    return "llm_error"


def llm_stream_error_sse(
    exc: BaseException,
    *,
    mapped: tuple[int, str] | None = None,
) -> str:
    """Format a client-visible ``seal.error`` SSE frame for stream failures."""
    from seal_core.chat.sse import format_seal_error_sse

    resolved = mapped if mapped is not None else llm_http_error(exc)
    if resolved is None:
        return format_seal_error_sse(
            code="error",
            message="Chat failed. See server logs for details.",
        )
    _, detail = resolved
    return format_seal_error_sse(code=llm_error_event_code(resolved), message=detail)


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
        return 503, rate_limit_user_message()
    throttled_provider = isinstance(
        root, (litellm.InternalServerError, litellm.APIError)
    ) and looks_like_rate_limit_text(str(root))
    if throttled_provider:
        return 503, rate_limit_user_message()
    if isinstance(root, litellm.APIError):
        return 502, _CLIENT_LLM_GENERIC
    if isinstance(root, litellm.InternalServerError):
        return 502, _CLIENT_LLM_GENERIC
    return None


# Backward-compatible alias for tests and callers.
def is_rate_limit_signal(status: int, text: str) -> bool:
    """True when an HTTP status or message body indicates LLM rate limiting."""
    return is_rate_limit_http(status, text)
