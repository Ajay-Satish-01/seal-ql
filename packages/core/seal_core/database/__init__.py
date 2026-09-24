"""Multi-database routing for Seal."""

from seal_core.database.config import (
    DEFAULT_DATABASE_ID,
    DatabaseConfigError,
    NetworkConnectionParams,
    clickhouse_default_port,
    database_id_from_metadata,
    infer_dialect,
    is_default_database_id,
    load_database_urls,
    normalize_connection_url,
    parse_network_url,
    planner_resources_for_database,
)
from seal_core.database.registry import (
    DatabaseBundle,
    DatabaseRegistry,
    UnknownDatabaseError,
    build_database_registry,
)

__all__ = [
    "DEFAULT_DATABASE_ID",
    "DatabaseBundle",
    "DatabaseConfigError",
    "NetworkConnectionParams",
    "DatabaseRegistry",
    "UnknownDatabaseError",
    "build_database_registry",
    "clickhouse_default_port",
    "database_id_from_metadata",
    "infer_dialect",
    "is_default_database_id",
    "load_database_urls",
    "normalize_connection_url",
    "parse_network_url",
    "planner_resources_for_database",
]
