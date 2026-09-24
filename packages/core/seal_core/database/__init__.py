"""Multi-database routing for Seal."""

from seal_core.database.config import (
    DEFAULT_DATABASE_ID,
    DatabaseConfigError,
    database_id_from_metadata,
    infer_dialect,
    is_default_database_id,
    load_database_urls,
    normalize_connection_url,
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
    "DatabaseRegistry",
    "UnknownDatabaseError",
    "build_database_registry",
    "database_id_from_metadata",
    "infer_dialect",
    "is_default_database_id",
    "load_database_urls",
    "normalize_connection_url",
    "planner_resources_for_database",
]
