# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Version numbers are bumped in lockstep across the API and SDKs; see [RELEASING.md](RELEASING.md).

## [Unreleased]

### Added

- **MySQL / MariaDB** (`mysql://`, `mysql+pymysql://`, `mariadb://`): `information_schema` introspection and async `aiomysql` execution with the same timeout, retry, and row-cap as Postgres.
- **SQLite** (`sqlite:///relative.db`, `sqlite:////absolute/path.db`, `sqlite:///:memory:`): `PRAGMA` / `sqlite_master` introspection and async `aiosqlite` execution. File URLs normalize to paths, matching DuckDB.
- **ClickHouse** (`clickhouse://`, `clickhouses://` for TLS): `system.tables` / `system.columns` introspection and `clickhouse-connect` execution in a thread pool.
- Optional live tests behind pytest markers `mysql` and `clickhouse` (`SEAL_TEST_MYSQL_URL` / `SEAL_TEST_CLICKHOUSE_URL`). Default CI does not require those servers.

Drivers are **optional extras** of `seal-core` / `seal-sql` / `seal-api` (`mysql`, `sqlite`, `clickhouse`, or `dialects`), not default-image dependencies. Default Compose stays Postgres + DuckDB. LLM-generated SQL still passes through the SQLGlot zero-trust validator and sanitizer for every dialect; ClickHouse mutations and DDL remain blocked.

Per-database catalog sync and vector RAG indexes are deferred ([#57](https://github.com/Ajay-Satish-01/seal-ql/issues/57), [#58](https://github.com/Ajay-Satish-01/seal-ql/issues/58)).

Docs: [docs/multi-database.md](docs/multi-database.md), [docs/zero-trust-sql.md](docs/zero-trust-sql.md), docs site `/docs/multi-database` and `/docs/zero-trust-sql`, `config/databases.example.yaml`.
