"""Tests for schema introspection — models and introspectors."""

import pytest
from seal_core.schema.models import (
    ColumnInfo,
    ColumnType,
    ContinuousAggregateInfo,
    DatabaseSchema,
    HypertableInfo,
    RelationshipInfo,
    TableKind,
    TableSchema,
)

# ============================================================
# Model unit tests
# ============================================================


class TestColumnInfo:
    def test_string_representation(self):
        col = ColumnInfo(
            name="email",
            data_type="VARCHAR(100)",
            normalized_type=ColumnType.STRING,
            nullable=False,
            is_primary_key=False,
        )
        assert "email" in str(col)
        assert "NOT NULL" in str(col)

    def test_pk_representation(self):
        col = ColumnInfo(
            name="id",
            data_type="INTEGER",
            normalized_type=ColumnType.INTEGER,
            nullable=False,
            is_primary_key=True,
        )
        assert "PK" in str(col)


class TestTableSchema:
    def test_column_names(self):
        table = TableSchema(
            name="users",
            columns=[
                ColumnInfo(name="id", data_type="INT", normalized_type=ColumnType.INTEGER),
                ColumnInfo(name="name", data_type="TEXT", normalized_type=ColumnType.STRING),
            ],
        )
        assert table.column_names == ["id", "name"]

    def test_primary_keys(self):
        table = TableSchema(
            name="users",
            columns=[
                ColumnInfo(
                    name="id",
                    data_type="INT",
                    normalized_type=ColumnType.INTEGER,
                    is_primary_key=True,
                ),
                ColumnInfo(name="name", data_type="TEXT", normalized_type=ColumnType.STRING),
            ],
        )
        assert table.primary_keys == ["id"]

    def test_get_column_case_insensitive(self):
        table = TableSchema(
            name="users",
            columns=[
                ColumnInfo(name="Email", data_type="TEXT", normalized_type=ColumnType.STRING),
            ],
        )
        assert table.get_column("email") is not None
        assert table.get_column("EMAIL") is not None
        assert table.get_column("nonexistent") is None

    def test_kind_defaults_to_table(self):
        table = TableSchema(name="users")
        assert table.kind == TableKind.TABLE

    def test_is_timescaledb(self):
        hypertable = TableSchema(name="events", kind=TableKind.HYPERTABLE)
        assert hypertable.is_timescaledb is True

        cagg = TableSchema(name="events_hourly", kind=TableKind.CONTINUOUS_AGGREGATE)
        assert cagg.is_timescaledb is True

        regular = TableSchema(name="users", kind=TableKind.TABLE)
        assert regular.is_timescaledb is False

    def test_matview_kind(self):
        mv = TableSchema(name="product_perf", kind=TableKind.MATERIALIZED_VIEW)
        assert mv.kind == TableKind.MATERIALIZED_VIEW
        assert mv.is_timescaledb is False


class TestDatabaseSchema:
    def _make_schema(self) -> DatabaseSchema:
        return DatabaseSchema(
            dialect="postgres",
            has_timescaledb=True,
            tables=[
                TableSchema(
                    name="orders",
                    kind=TableKind.TABLE,
                    columns=[
                        ColumnInfo(
                            name="id",
                            data_type="INTEGER",
                            normalized_type=ColumnType.INTEGER,
                            is_primary_key=True,
                            nullable=False,
                        ),
                        ColumnInfo(
                            name="amount",
                            data_type="NUMERIC(10,2)",
                            normalized_type=ColumnType.NUMERIC,
                        ),
                    ],
                    row_count=500,
                ),
                TableSchema(
                    name="product_performance",
                    kind=TableKind.MATERIALIZED_VIEW,
                    columns=[
                        ColumnInfo(
                            name="product_id",
                            data_type="INTEGER",
                            normalized_type=ColumnType.INTEGER,
                        ),
                        ColumnInfo(
                            name="total_revenue",
                            data_type="NUMERIC",
                            normalized_type=ColumnType.NUMERIC,
                        ),
                    ],
                ),
                TableSchema(
                    name="events",
                    kind=TableKind.HYPERTABLE,
                    columns=[
                        ColumnInfo(
                            name="time",
                            data_type="TIMESTAMPTZ",
                            normalized_type=ColumnType.TIMESTAMP,
                        ),
                        ColumnInfo(
                            name="event_type",
                            data_type="VARCHAR(50)",
                            normalized_type=ColumnType.STRING,
                        ),
                    ],
                    hypertable_info=HypertableInfo(
                        time_column="time",
                        chunk_interval="7 days",
                        compression_enabled=True,
                    ),
                ),
                TableSchema(
                    name="events_hourly",
                    kind=TableKind.CONTINUOUS_AGGREGATE,
                    columns=[
                        ColumnInfo(
                            name="bucket",
                            data_type="TIMESTAMPTZ",
                            normalized_type=ColumnType.TIMESTAMP,
                        ),
                        ColumnInfo(
                            name="event_count",
                            data_type="BIGINT",
                            normalized_type=ColumnType.INTEGER,
                        ),
                    ],
                    continuous_aggregate_info=ContinuousAggregateInfo(
                        source_hypertable="public.events",
                        refresh_interval="30 minutes",
                    ),
                ),
            ],
            relationships=[
                RelationshipInfo(
                    from_table="orders",
                    from_column="customer_id",
                    to_table="customers",
                    to_column="id",
                ),
            ],
        )

    def test_table_names(self):
        schema = self._make_schema()
        assert "orders" in schema.table_names
        assert "events" in schema.table_names
        assert "events_hourly" in schema.table_names
        assert "product_performance" in schema.table_names

    def test_get_table(self):
        schema = self._make_schema()
        assert schema.get_table("orders") is not None
        assert schema.get_table("ORDERS") is not None  # case-insensitive
        assert schema.get_table("nonexistent") is None

    def test_get_tables_by_kind(self):
        schema = self._make_schema()
        hypertables = schema.get_tables_by_kind(TableKind.HYPERTABLE)
        assert len(hypertables) == 1
        assert hypertables[0].name == "events"

        caggs = schema.get_tables_by_kind(TableKind.CONTINUOUS_AGGREGATE)
        assert len(caggs) == 1
        assert caggs[0].name == "events_hourly"

        matviews = schema.get_tables_by_kind(TableKind.MATERIALIZED_VIEW)
        assert len(matviews) == 1

    def test_prompt_context_includes_timescaledb(self):
        schema = self._make_schema()
        ctx = schema.to_prompt_context()

        # Should include TimescaleDB status
        assert "TimescaleDB extension: ENABLED" in ctx

        # Should include table kinds
        assert "[hypertable]" in ctx
        assert "[continuous_aggregate]" in ctx
        assert "[materialized_view]" in ctx

        # Should include hypertable metadata
        assert "time_column=time" in ctx
        assert "chunk_interval=7 days" in ctx
        assert "compression=enabled" in ctx

        # Should include cagg metadata
        assert "source=public.events" in ctx
        assert "refresh_interval=30 minutes" in ctx

        # Should include relationships
        assert "orders.customer_id" in ctx

        # Should include row counts
        assert "~500 rows" in ctx

    def test_prompt_context_without_timescaledb(self):
        schema = DatabaseSchema(
            dialect="duckdb",
            has_timescaledb=False,
            tables=[
                TableSchema(
                    name="users",
                    kind=TableKind.TABLE,
                    columns=[
                        ColumnInfo(
                            name="id",
                            data_type="INTEGER",
                            normalized_type=ColumnType.INTEGER,
                        ),
                    ],
                ),
            ],
        )
        ctx = schema.to_prompt_context()
        assert "TimescaleDB" not in ctx
        assert "TABLE public.users" in ctx


class TestDuckDBIntrospector:
    """Test DuckDB introspector with an in-memory database."""

    @pytest.mark.asyncio
    async def test_introspect_empty_database(self):
        from seal_core.schema.duckdb import DuckDBIntrospector

        introspector = DuckDBIntrospector(":memory:")
        schema = await introspector.introspect()
        await introspector.close()

        assert schema.dialect == "duckdb"
        assert schema.has_timescaledb is False

    @pytest.mark.asyncio
    async def test_introspect_with_tables(self):
        import duckdb
        from seal_core.schema.duckdb import DuckDBIntrospector

        # Create a test database with known schema
        conn = duckdb.connect(":memory:")
        conn.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL,
                email VARCHAR,
                active BOOLEAN DEFAULT true
            )
        """)
        conn.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                amount DECIMAL(10,2),
                created_at TIMESTAMP
            )
        """)
        conn.execute("INSERT INTO users VALUES (1, 'Alice', 'alice@test.com', true)")
        conn.execute("INSERT INTO orders VALUES (1, 1, 99.99, '2024-01-01')")

        # Use the same connection via the introspector
        introspector = DuckDBIntrospector.__new__(DuckDBIntrospector)
        introspector._conn = conn
        introspector._connection_string = ":memory:"

        schema = await introspector.introspect()

        assert schema.dialect == "duckdb"
        assert len(schema.tables) >= 2

        users_table = schema.get_table("users")
        assert users_table is not None
        assert users_table.kind == TableKind.TABLE
        assert len(users_table.columns) == 4
        assert users_table.get_column("id") is not None
        assert users_table.get_column("id").is_primary_key is True
        assert users_table.row_count == 1

        orders_table = schema.get_table("orders")
        assert orders_table is not None
        assert orders_table.get_column("amount") is not None

        conn.close()
