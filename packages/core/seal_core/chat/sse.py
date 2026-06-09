"""SSE helpers for chat streaming."""

from __future__ import annotations

from seal_core.serialization import safe_json_dumps


def format_seal_error_sse(*, code: str, message: str) -> str:
    """Format a ``seal.error`` SSE event for client-visible stream failures."""
    payload = {"code": code, "message": message}
    return f"event: seal.error\ndata: {safe_json_dumps(payload)}\n\n"


def format_openai_sse_delta(content: str) -> str:
    """Format one OpenAI-style ``data:`` chunk for streamed assistant text."""
    payload = {
        "object": "chat.completion.chunk",
        "choices": [
            {
                "index": 0,
                "delta": {"content": content},
                "finish_reason": None,
            }
        ],
    }
    return f"data: {safe_json_dumps(payload)}\n\n"
