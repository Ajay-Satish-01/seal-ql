"""Registry of named database connections (introspector + executor per id)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from seal_sql.executor import QueryExecutor

from seal_core.database.config import (
    DEFAULT_DATABASE_ID,
    DatabaseConfigError,
    infer_dialect,
    is_default_database_id,
    load_database_urls,
    normalize_connection_url,
)
from seal_core.schema.introspector import get_introspector

if TYPE_CHECKING:
    from seal_core.schema.introspector import SchemaIntrospector
    from seal_core.settings import Settings

logger = logging.getLogger(__name__)


class UnknownDatabaseError(LookupError):
    """Raised when a client requests an unregistered database_id."""

    def __init__(self, database_id: str) -> None:
        self.database_id = database_id
        super().__init__(f"Unknown database_id: {database_id!r}")


@dataclass(frozen=True)
class DatabaseBundle:
    """Introspector and executor pair for one configured database."""

    database_id: str
    dialect: str
    url: str
    introspector: SchemaIntrospector
    executor: QueryExecutor


class DatabaseRegistry:
    """Lookup table for pre-configured database backends."""

    def __init__(self, bundles: dict[str, DatabaseBundle]) -> None:
        if DEFAULT_DATABASE_ID not in bundles:
            raise ValueError(f"Registry must include {DEFAULT_DATABASE_ID!r}")
        self._bundles = dict(bundles)

    def get(self, database_id: str) -> DatabaseBundle:
        bundle = self._bundles.get(database_id)
        if bundle is None:
            raise UnknownDatabaseError(database_id)
        return bundle

    def list_ids(self) -> list[str]:
        return sorted(self._bundles.keys())

    @property
    def default(self) -> DatabaseBundle:
        return self._bundles[DEFAULT_DATABASE_ID]

    async def close(self) -> None:
        seen: set[int] = set()
        for bundle in self._bundles.values():
            for resource in (bundle.executor, bundle.introspector):
                key = id(resource)
                if key in seen:
                    continue
                seen.add(key)
                await resource.close()


def build_database_registry(settings: Settings) -> DatabaseRegistry:
    """Build a registry from Settings (sync — connections open on first use)."""
    try:
        entries = load_database_urls(
            database_url=settings.database_url,
            seal_databases=settings.seal_databases,
            seal_databases_path=settings.seal_databases_path,
        )
    except DatabaseConfigError:
        raise
    except ValueError as exc:
        raise DatabaseConfigError(str(exc)) from exc

    if len(entries) > 1:
        extra_ids = [db_id for db_id in entries if not is_default_database_id(db_id)]
        logger.warning(
            "Multiple databases registered (%s). Catalog, semantic layer, and vector "
            "RAG apply to %r only; other ids use introspected schema without catalog hints.",
            extra_ids,
            DEFAULT_DATABASE_ID,
        )

    bundles: dict[str, DatabaseBundle] = {}
    for database_id, url in entries.items():
        dialect = infer_dialect(url)
        connection_url = normalize_connection_url(url)
        logger.info("Registering database %r (dialect=%s)", database_id, dialect)
        bundles[database_id] = DatabaseBundle(
            database_id=database_id,
            dialect=dialect,
            url=connection_url,
            introspector=get_introspector(dialect, connection_url),
            executor=QueryExecutor(dialect, connection_url),
        )
    return DatabaseRegistry(bundles)
