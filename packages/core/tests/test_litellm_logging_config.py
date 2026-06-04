"""Tests for LiteLLM logging suppression."""

from __future__ import annotations

import asyncio
import io
import sys

import litellm
import pytest
from seal_core.llm.logging_config import configure_litellm_logging


def test_configure_suppresses_litellm_feedback_banner() -> None:
    configure_litellm_logging()
    assert litellm.set_verbose is False
    assert litellm.suppress_debug_info is True

    buffer = io.StringIO()
    stderr = sys.stderr
    sys.stderr = buffer
    try:

        async def _fail() -> None:
            from litellm import aembedding

            await aembedding(model="openai/text-embedding-3-small", input=["hi"])

        with pytest.raises(litellm.InternalServerError):
            asyncio.run(_fail())
    finally:
        sys.stderr = stderr

    output = buffer.getvalue()
    assert "Give Feedback" not in output
    assert "_turn_on_debug" not in output
