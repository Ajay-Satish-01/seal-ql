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

from seal.client import AsyncSeal, Seal
from seal.exceptions import (
    ConnectionError,
    QueryError,
    SealConnectionError,
    SealError,
    ServerError,
)
from seal.models import (
    ChartSpec,
    ChartType,
    ColumnMetadata,
    DatabaseSchema,
    HealthResponse,
    QueryResponse,
)

__all__ = [
    # Clients
    "Seal",
    "AsyncSeal",
    # Models
    "QueryResponse",
    "ColumnMetadata",
    "ChartSpec",
    "ChartType",
    "HealthResponse",
    "DatabaseSchema",
    # Exceptions
    "SealError",
    "SealConnectionError",
    "ConnectionError",
    "QueryError",
    "ServerError",
]
