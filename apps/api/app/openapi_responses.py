"""Shared OpenAPI response definitions."""

from __future__ import annotations

UNAUTHORIZED_RESPONSE: dict[int, dict[str, object]] = {
    401: {
        "description": "Invalid or missing API key",
        "content": {
            "application/json": {
                "example": {"detail": "Invalid or missing API key"},
            }
        },
    }
}

UNKNOWN_DATABASE_RESPONSE: dict[int, dict[str, object]] = {
    404: {
        "description": "Unknown database_id",
        "content": {
            "application/json": {
                "example": {"detail": "unknown_database_id"},
            }
        },
    }
}

AUTH_AND_DATABASE_RESPONSES: dict[int, dict[str, object]] = {
    **UNAUTHORIZED_RESPONSE,
    **UNKNOWN_DATABASE_RESPONSE,
}

QUERY_OUT_OF_SCOPE_RESPONSE: dict[int, dict[str, object]] = {
    400: {
        "description": "Guardrails rejected the query (out of scope)",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/QueryOutOfScopeErrorResponse"},
                "example": {
                    "detail": {
                        "detail": "query_out_of_scope",
                        "reason": "off-topic pattern",
                        "suggested_queries": [
                            "Show order count by month",
                            "What tables are available?",
                        ],
                    }
                },
            }
        },
    }
}

QUERY_ENDPOINT_RESPONSES: dict[int, dict[str, object]] = {
    **AUTH_AND_DATABASE_RESPONSES,
    **QUERY_OUT_OF_SCOPE_RESPONSE,
}

CHAT_SUCCESS_RESPONSE: dict[int, dict[str, object]] = {
    200: {
        "description": (
            "JSON ChatResponse when stream=false; SSE (seal.meta + answer chunks) when stream=true"
        ),
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ChatResponse"},
            },
            "text/event-stream": {
                "schema": {"$ref": "#/components/schemas/ChatStreamMeta"},
                "description": (
                    "SSE wire format: `event: seal.meta` whose `data:` line matches "
                    "ChatStreamMeta, then OpenAI-style `data:` answer chunks, then `data: [DONE]`"
                ),
            },
        },
    }
}

CHAT_ENDPOINT_RESPONSES: dict[int, dict[str, object]] = {
    **CHAT_SUCCESS_RESPONSE,
    **AUTH_AND_DATABASE_RESPONSES,
}
