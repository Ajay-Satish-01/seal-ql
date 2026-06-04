"""FastAPI helpers for LLM failures."""

from __future__ import annotations

import logging

from fastapi import HTTPException
from seal_core.llm.http_errors import llm_http_error

logger = logging.getLogger(__name__)


def raise_for_llm_failure(exc: BaseException) -> None:
    """Re-raise as HTTPException when ``exc`` (or its cause) is a LiteLLM error."""
    mapped = llm_http_error(exc)
    if mapped is None:
        return
    status_code, detail = mapped
    logger.error("LLM request failed: %s", exc)
    raise HTTPException(status_code=status_code, detail=detail) from exc
