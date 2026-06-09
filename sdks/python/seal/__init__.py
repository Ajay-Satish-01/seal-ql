"""Seal Python SDK.

Usage:
    from seal import Seal

    with Seal("http://localhost:8000") as client:
        result = client.query("Show me monthly revenue")
        print(result.sql)
        print(result.results)

Async usage:
    from seal import AsyncSeal

    async with AsyncSeal("http://localhost:8000") as client:
        result = await client.query("Show me monthly revenue")
"""

from seal._http_errors import RATE_LIMIT_USER_MESSAGE, is_rate_limit_signal
from seal._sse import ChatStreamEvent
from seal.client import AsyncSeal, Seal
from seal.exceptions import (
    ConnectionError,
    QueryError,
    QueryOutOfScopeError,
    SealConnectionError,
    SealError,
    ServerError,
)
from seal.models import (
    CatalogResponse,
    ChartSpec,
    ChartType,
    ChatMetadata,
    ChatResponse,
    ColumnMetadata,
    DatabaseSchema,
    EnhancementMetadata,
    HealthResponse,
    QueryMetadata,
    QueryResponse,
    ReasoningMetadata,
    ScopeMetadata,
)
from seal.rate_limit import looks_like_rate_limit_text, rate_limit_markers

__all__ = [
    # Clients
    "Seal",
    "AsyncSeal",
    # Models
    "QueryResponse",
    "QueryMetadata",
    "ColumnMetadata",
    "ChartSpec",
    "ChartType",
    "HealthResponse",
    "DatabaseSchema",
    "ChatResponse",
    "ChatMetadata",
    "EnhancementMetadata",
    "ScopeMetadata",
    "ReasoningMetadata",
    "CatalogResponse",
    "ChatStreamEvent",
    # Rate limiting
    "RATE_LIMIT_USER_MESSAGE",
    "is_rate_limit_signal",
    "looks_like_rate_limit_text",
    "rate_limit_markers",
    # Exceptions
    "SealError",
    "SealConnectionError",
    "ConnectionError",
    "QueryError",
    "QueryOutOfScopeError",
    "ServerError",
]
