"""Load named database connection entries for DatabaseRegistry."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, unquote, urlparse

import yaml

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_ID = "default"

_MYSQL_SCHEMES = frozenset({"mysql", "mariadb"})
_SQLITE_SCHEMES = frozenset({"sqlite"})
_CLICKHOUSE_SCHEMES = frozenset({"clickhouse", "clickhouses"})
_POSTGRES_SCHEMES = frozenset({"postgres", "postgresql"})

_SUPPORTED_SCHEMES_MSG = (
    "postgresql/postgres, duckdb, mysql/mariadb, sqlite, clickhouse"
)


class DatabaseConfigError(ValueError):
    """Invalid database configuration."""


@dataclass(frozen=True)
class NetworkConnectionParams:
    """Hosted-database connection fields parsed from a URL."""

    host: str
    port: int
    user: str
    password: str
    database: str
    secure: bool = False


def is_default_database_id(database_id: str) -> bool:
    """Return True when database_id refers to the primary configured database."""
    return database_id == DEFAULT_DATABASE_ID


def database_id_from_metadata(metadata: dict[str, Any] | None) -> str:
    """Read database_id from enhancement/turn metadata with a stable default."""
    if not metadata:
        return DEFAULT_DATABASE_ID
    return str(metadata.get("database_id", DEFAULT_DATABASE_ID))


def _scheme_base(scheme: str) -> str:
    """Strip SQLAlchemy-style driver suffixes (``mysql+pymysql`` → ``mysql``)."""
    return scheme.split("+", 1)[0].lower()


def infer_dialect(url: str) -> str:
    """Infer dialect from a connection URL or path.

    Raises:
        DatabaseConfigError: When the URL scheme is not supported.
    """
    lower = url.lower().strip()
    parsed = urlparse(lower)
    scheme = _scheme_base(parsed.scheme)
    if scheme in _POSTGRES_SCHEMES:
        return "postgres"
    if scheme in _MYSQL_SCHEMES:
        return "mysql"
    if scheme in _SQLITE_SCHEMES:
        return "sqlite"
    if scheme in _CLICKHOUSE_SCHEMES:
        return "clickhouse"
    if scheme == "duckdb" or lower == ":memory:" or lower.startswith(":memory:"):
        return "duckdb"
    if scheme and "://" in lower:
        msg = (
            f"Unsupported database URL scheme in {url!r}; "
            f"supported schemes: {_SUPPORTED_SCHEMES_MSG}"
        )
        raise DatabaseConfigError(msg)
    return "duckdb"


def normalize_connection_url(url: str) -> str:
    """Return the concrete connection string/path used by drivers.

    DuckDB and SQLite Python drivers accept file paths, not ``scheme:///`` URLs.
    Seal's config accepts the URL form for consistency with hosted databases,
    then normalizes file-backed URLs before constructing introspectors/executors.

    Hosted dialects (Postgres, MySQL/MariaDB, ClickHouse) are passed through.
    """
    stripped = url.strip()
    dialect = infer_dialect(stripped)
    if dialect == "duckdb":
        return _normalize_file_url(
            stripped,
            scheme="duckdb",
            original=url,
            relative_three_slash=False,
        )
    if dialect == "sqlite":
        return _normalize_file_url(
            stripped,
            scheme="sqlite",
            original=url,
            relative_three_slash=True,
        )
    return stripped


def _normalize_file_url(
    stripped: str,
    *,
    scheme: str,
    original: str,
    relative_three_slash: bool,
) -> str:
    """Normalize ``scheme:///path`` URLs to driver file paths or ``:memory:``.

    When ``relative_three_slash`` is True (SQLite SQLAlchemy form):
    ``sqlite:///relative.db`` → ``relative.db``;
    ``sqlite:////absolute/path.db`` → ``/absolute/path.db``;
    ``sqlite:///:memory:`` → ``:memory:``.

    When False (DuckDB): ``duckdb:///data/file.duckdb`` keeps the leading slash
    as an absolute path.
    """
    parsed = urlparse(stripped)
    parsed_scheme = _scheme_base(parsed.scheme)
    if parsed_scheme != scheme:
        return stripped
    if parsed.params or parsed.query or parsed.fragment:
        raise DatabaseConfigError(
            f"{scheme.upper()} URL {original!r} must not include params, query, or fragment"
        )
    if parsed.netloc:
        raise DatabaseConfigError(
            f"{scheme.upper()} URL {original!r} must be a local path like {scheme}:///data/file.db"
        )
    path = unquote(parsed.path)
    if path in {"", "/"}:
        raise DatabaseConfigError(f"{scheme.upper()} URL {original!r} requires a database path")
    if path == "/:memory:":
        return ":memory:"
    if relative_three_slash:
        # Four slashes: sqlite:////abs/path.db → path='//abs/path.db'
        if path.startswith("//"):
            return path[1:]
        # Three slashes: sqlite:///relative.db → path='/relative.db'
        return path.lstrip("/")
    return path


def clickhouse_default_port(url: str) -> int:
    """HTTP 8123, or HTTPS 8443 when the scheme is ``clickhouses://``."""
    scheme = _scheme_base(urlparse(url.strip()).scheme)
    return 8443 if scheme == "clickhouses" else 8123


def parse_network_url(
    url: str,
    *,
    default_port: int,
    default_user: str = "",
    default_database: str = "",
) -> NetworkConnectionParams:
    """Parse a hosted SQL URL into driver connection fields.

    Strips SQLAlchemy driver suffixes (``mysql+pymysql://`` → ``mysql://``).
    ``clickhouses://`` and ``?secure=true`` enable TLS.
    """
    stripped = url.strip()
    parsed_original = urlparse(stripped)
    scheme = parsed_original.scheme
    if "+" in scheme:
        base = scheme.split("+", 1)[0]
        stripped = stripped.replace(f"{scheme}://", f"{base}://", 1)
        parsed_original = urlparse(stripped)

    parsed = parsed_original
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    database = unquote(parsed.path.lstrip("/")) if parsed.path else ""
    if "/" in database:
        database = database.split("/", 1)[0]
    secure = _scheme_base(parsed.scheme) == "clickhouses" or query.get("secure", "").lower() in {
        "1",
        "true",
        "yes",
    }
    host = unquote(parsed.hostname) if parsed.hostname else "localhost"
    user = unquote(parsed.username) if parsed.username else default_user
    password = unquote(parsed.password) if parsed.password else ""
    return NetworkConnectionParams(
        host=host,
        port=parsed.port or default_port,
        user=user,
        password=password,
        database=database or default_database,
        secure=secure,
    )


def planner_resources_for_database(
    database_id: str,
    *,
    catalog: Any | None,
    semantic_registry: Any | None,
) -> tuple[Any | None, Any | None]:
    """Return catalog/semantic only for the default database."""
    if is_default_database_id(database_id):
        return semantic_registry, catalog
    return None, None


def _merge_non_default_entries(
    entries: dict[str, str],
    new_entries: dict[str, str],
    *,
    source: str,
) -> None:
    """Add named entries, ignoring any attempt to override the default id."""
    for db_id, url in new_entries.items():
        if is_default_database_id(db_id):
            logger.warning(
                "Ignoring %r entry in %s; DATABASE_URL defines default",
                DEFAULT_DATABASE_ID,
                source,
            )
            continue
        entries[db_id] = url


def load_database_urls(
    *,
    database_url: str,
    seal_databases: str | None = None,
    seal_databases_path: str | None = None,
) -> dict[str, str]:
    """Merge default DATABASE_URL with optional JSON env and YAML file entries.

    The ``default`` id always comes from ``database_url``. Additional ids are
    loaded from ``seal_databases_path`` (when the file exists) and ``seal_databases``
    JSON (which can add or override non-default entries).

    Note: duplicate keys in YAML source are resolved by the parser (last wins);
    use distinct ids per entry.
    """
    entries: dict[str, str] = {DEFAULT_DATABASE_ID: database_url.strip()}

    if seal_databases_path:
        path = Path(seal_databases_path)
        if path.is_file():
            _merge_non_default_entries(
                entries,
                _parse_config_file(path),
                source=str(path),
            )
        elif path.exists():
            logger.warning("SEAL_DATABASES_PATH is not a file: %s", path)

    if seal_databases:
        _merge_non_default_entries(
            entries,
            _parse_json_entries(seal_databases),
            source="SEAL_DATABASES",
        )

    _validate_entries(entries)
    return entries


def _parse_config_file(path: Path) -> dict[str, str]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise DatabaseConfigError(f"Invalid YAML in database config {path}: {exc}") from exc
    if raw is None:
        raise DatabaseConfigError(f"Database config at {path} is empty")
    if not isinstance(raw, dict):
        raise DatabaseConfigError(f"Database config at {path} must be a YAML mapping")
    databases = raw.get("databases", raw)
    if not isinstance(databases, dict):
        raise DatabaseConfigError(f"Database config at {path} must contain a 'databases' mapping")
    return _normalize_mapping(databases, source=str(path))


def _parse_json_entries(raw_json: str) -> dict[str, str]:
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise DatabaseConfigError(f"SEAL_DATABASES is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise DatabaseConfigError("SEAL_DATABASES must be a JSON object")
    return _normalize_mapping(parsed, source="SEAL_DATABASES")


def _normalize_mapping(raw: dict[Any, Any], *, source: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for key, value in raw.items():
        db_id = str(key).strip()
        if not db_id:
            raise DatabaseConfigError(f"Empty database id in {source}")
        url = _extract_url(value, db_id=db_id, source=source)
        if db_id in entries:
            raise DatabaseConfigError(f"Duplicate database id {db_id!r} in {source}")
        entries[db_id] = url
    return entries


def _extract_url(value: object, *, db_id: str, source: str) -> str:
    if isinstance(value, str):
        url = value.strip()
    elif isinstance(value, dict):
        url_value = value.get("url")
        if not isinstance(url_value, str) or not url_value.strip():
            raise DatabaseConfigError(f"Database {db_id!r} in {source} requires a non-empty 'url'")
        url = url_value.strip()
    else:
        raise DatabaseConfigError(
            f"Database {db_id!r} in {source} must be a string or mapping with 'url'"
        )
    if not url:
        raise DatabaseConfigError(f"Database {db_id!r} in {source} has an empty url")
    infer_dialect(url)
    return url


def _validate_entries(entries: dict[str, str]) -> None:
    if DEFAULT_DATABASE_ID not in entries:
        raise DatabaseConfigError(f"Missing required database id {DEFAULT_DATABASE_ID!r}")
    for db_id, url in entries.items():
        if not db_id.strip():
            raise DatabaseConfigError("Database ids must be non-empty")
        if not url.strip():
            raise DatabaseConfigError(f"Database {db_id!r} has an empty connection url")
