"""Intelligence Connector Python SDK.

Usage:
    from intelligence_connector import IntelligenceConnector

    with IntelligenceConnector("http://localhost:8000") as client:
        result = client.query("Show me monthly revenue")
        print(result.sql)
        print(result.results)

Async usage:
    from intelligence_connector import AsyncIntelligenceConnector

    async with AsyncIntelligenceConnector("http://localhost:8000") as client:
        result = await client.query("Show me monthly revenue")
"""

from intelligence_connector.client import AsyncIntelligenceConnector, IntelligenceConnector
from intelligence_connector.exceptions import (
    ConnectionError,
    IntelligenceConnectorError,
    QueryError,
    ServerError,
)
from intelligence_connector.models import (
    ChartSpec,
    ChartType,
    ColumnMetadata,
    DatabaseSchema,
    HealthResponse,
    QueryResponse,
)

__all__ = [
    # Clients
    "IntelligenceConnector",
    "AsyncIntelligenceConnector",
    # Models
    "QueryResponse",
    "ColumnMetadata",
    "ChartSpec",
    "ChartType",
    "HealthResponse",
    "DatabaseSchema",
    # Exceptions
    "IntelligenceConnectorError",
    "ConnectionError",
    "QueryError",
    "ServerError",
]
