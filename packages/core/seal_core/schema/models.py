"""Canonical data models for database schema representation.

These models are the single source of truth for schema metadata throughout
the entire Seal system. Every introspector (DuckDB, Postgres)
produces these models, and every downstream consumer (planner, validator) reads them.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ColumnType(StrEnum):
    """Normalized column types across all supported databases."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    TIMESTAMP = "timestamp"
    NUMERIC = "numeric"
    JSON = "json"
    ARRAY = "array"
    OTHER = "other"


class TableKind(StrEnum):
    """The kind of relation in the database.

    Distinguishing these is critical because:
    - The LLM needs to know what it can query (e.g., matviews are pre-aggregated)
    - Hypertables and continuous aggregates have time-series semantics
    - The validator may need to handle these differently
    """

    TABLE = "table"
    VIEW = "view"
    MATERIALIZED_VIEW = "materialized_view"
    HYPERTABLE = "hypertable"
    CONTINUOUS_AGGREGATE = "continuous_aggregate"


class ColumnInfo(BaseModel):
    """Metadata for a single database column."""

    name: str = Field(description="Column name")
    data_type: str = Field(description="Raw database type (e.g., 'VARCHAR(100)')")
    normalized_type: ColumnType = Field(description="Normalized portable type")
    nullable: bool = Field(default=True, description="Whether the column allows NULL values")
    is_primary_key: bool = Field(default=False, description="Whether this column is a primary key")
    default_value: str | None = Field(default=None, description="Default value expression")
    description: str | None = Field(default=None, description="Column comment/description")

    def __str__(self) -> str:
        pk = " PK" if self.is_primary_key else ""
        null = " NULL" if self.nullable else " NOT NULL"
        return f"{self.name} {self.data_type}{pk}{null}"


class HypertableInfo(BaseModel):
    """TimescaleDB-specific metadata for a hypertable.

    Hypertables are the core abstraction in TimescaleDB — they look like
    regular tables but are automatically partitioned by time for performance.
    """

    time_column: str = Field(description="The time-partitioning column name")
    chunk_interval: str | None = Field(
        default=None, description="Chunk time interval (e.g., '7 days')"
    )
    compression_enabled: bool = Field(
        default=False, description="Whether compression is enabled on this hypertable"
    )
    num_chunks: int | None = Field(default=None, description="Number of chunks")


class ContinuousAggregateInfo(BaseModel):
    """TimescaleDB continuous aggregate metadata.

    Continuous aggregates are materialized views that are incrementally updated
    by TimescaleDB in the background. They're ideal for time-series analytics
    because the LLM can query them directly for pre-aggregated data.
    """

    source_hypertable: str = Field(description="The hypertable this aggregate reads from")
    view_definition: str | None = Field(
        default=None, description="The SQL definition of the continuous aggregate"
    )
    refresh_interval: str | None = Field(
        default=None, description="How often the aggregate refreshes (e.g., '1 hour')"
    )
    refresh_start_offset: str | None = Field(
        default=None, description="Start offset for refresh window"
    )
    refresh_end_offset: str | None = Field(
        default=None, description="End offset for refresh window"
    )


class RelationshipInfo(BaseModel):
    """A foreign key relationship between two tables."""

    from_table: str = Field(description="Source table (the one with the FK)")
    from_column: str = Field(description="Source column")
    to_table: str = Field(description="Referenced table")
    to_column: str = Field(description="Referenced column")
    constraint_name: str | None = Field(default=None, description="FK constraint name")

    def __str__(self) -> str:
        return f"{self.from_table}.{self.from_column} → {self.to_table}.{self.to_column}"


class TableSchema(BaseModel):
    """Full schema for a single database table, view, or materialized view."""

    name: str = Field(description="Table name")
    schema_name: str = Field(default="public", description="Schema/namespace")
    kind: TableKind = Field(default=TableKind.TABLE, description="Type of relation")
    columns: list[ColumnInfo] = Field(default_factory=list, description="Columns in the table")
    row_count: int | None = Field(default=None, description="Approximate row count (if available)")
    description: str | None = Field(default=None, description="Table comment/description")

    # TimescaleDB-specific (only populated for hypertables / continuous aggregates)
    hypertable_info: HypertableInfo | None = Field(
        default=None, description="TimescaleDB hypertable metadata (if applicable)"
    )
    continuous_aggregate_info: ContinuousAggregateInfo | None = Field(
        default=None, description="TimescaleDB continuous aggregate metadata (if applicable)"
    )

    @property
    def column_names(self) -> list[str]:
        """Get all column names."""
        return [col.name for col in self.columns]

    @property
    def primary_keys(self) -> list[str]:
        """Get primary key column names."""
        return [col.name for col in self.columns if col.is_primary_key]

    @property
    def is_timescaledb(self) -> bool:
        """Whether this is a TimescaleDB-managed relation."""
        return self.kind in (TableKind.HYPERTABLE, TableKind.CONTINUOUS_AGGREGATE)

    def get_column(self, name: str) -> ColumnInfo | None:
        """Look up a column by name (case-insensitive)."""
        name_lower = name.lower()
        for col in self.columns:
            if col.name.lower() == name_lower:
                return col
        return None

    def __str__(self) -> str:
        kind_label = f" [{self.kind.value}]" if self.kind != TableKind.TABLE else ""
        cols = ", ".join(str(c) for c in self.columns)
        return f"{self.schema_name}.{self.name}{kind_label} ({cols})"


class DatabaseSchema(BaseModel):
    """Complete schema for an entire database connection.

    This is the top-level model passed to the query planner and SQL validator.
    It contains all tables (including views, matviews, hypertables, continuous
    aggregates), their columns, and relationships.
    """

    dialect: str = Field(description="Database dialect: 'postgres' or 'duckdb'")
    tables: list[TableSchema] = Field(default_factory=list, description="All tables/views/matviews")
    relationships: list[RelationshipInfo] = Field(
        default_factory=list, description="Foreign key relationships"
    )
    has_timescaledb: bool = Field(
        default=False, description="Whether TimescaleDB extension is available"
    )

    @property
    def table_names(self) -> list[str]:
        """Get all table names."""
        return [t.name for t in self.tables]

    def get_table(self, name: str) -> TableSchema | None:
        """Look up a table by name (case-insensitive)."""
        name_lower = name.lower()
        for table in self.tables:
            if table.name.lower() == name_lower:
                return table
        return None

    def get_tables_by_kind(self, kind: TableKind) -> list[TableSchema]:
        """Get all tables of a specific kind."""
        return [t for t in self.tables if t.kind == kind]

    def to_prompt_context(self) -> str:
        """Serialize the schema into a compact string for LLM prompt injection.

        This produces a concise but complete representation that the LLM can
        use to understand the database structure without wasting tokens.
        Includes table kinds and TimescaleDB metadata when relevant.
        """
        lines: list[str] = [f"Database dialect: {self.dialect}"]
        if self.has_timescaledb:
            lines.append("TimescaleDB extension: ENABLED")
        lines.append("")

        for table in self.tables:
            kind_label = f" [{table.kind.value}]" if table.kind != TableKind.TABLE else ""
            lines.append(f"TABLE {table.schema_name}.{table.name}{kind_label}")

            for col in table.columns:
                pk = " [PK]" if col.is_primary_key else ""
                null = "" if col.nullable else " NOT NULL"
                lines.append(f"  - {col.name}: {col.data_type}{pk}{null}")

            if table.row_count is not None:
                lines.append(f"  (~{table.row_count:,} rows)")

            # TimescaleDB metadata in prompt context
            if table.hypertable_info:
                ht = table.hypertable_info
                lines.append(f"  [hypertable] time_column={ht.time_column}")
                if ht.chunk_interval:
                    lines.append(f"  [hypertable] chunk_interval={ht.chunk_interval}")
                if ht.compression_enabled:
                    lines.append("  [hypertable] compression=enabled")

            if table.continuous_aggregate_info:
                ca = table.continuous_aggregate_info
                lines.append(f"  [continuous_aggregate] source={ca.source_hypertable}")
                if ca.refresh_interval:
                    lines.append(f"  [continuous_aggregate] refresh_interval={ca.refresh_interval}")

            lines.append("")

        if self.relationships:
            lines.append("RELATIONSHIPS:")
            for rel in self.relationships:
                lines.append(f"  {rel}")
            lines.append("")

        return "\n".join(lines)
