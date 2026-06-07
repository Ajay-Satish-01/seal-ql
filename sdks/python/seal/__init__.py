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
    # Exceptions
    "SealError",
    "SealConnectionError",
    "ConnectionError",
    "QueryError",
    "QueryOutOfScopeError",
    "ServerError",
]
