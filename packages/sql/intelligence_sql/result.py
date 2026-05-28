"""QueryResult — normalized container for query execution results.

Wraps raw database rows with metadata (column types, execution time,
truncation status) and provides export methods for Polars, Pandas,
and plain JSON. This is the universal return type from QueryExecutor.
"""

from __future__ import annotations

import datetime
import decimal
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ColumnMetadata:
    """Metadata for a single result column.

    Attributes:
        name: Column name as returned by the database.
        type: Python type name (e.g., 'int', 'str', 'datetime').
        nullable: Whether the column contained any NULL values in the result set.
    """

    name: str
    type: str = "str"
    nullable: bool = True


@dataclass(frozen=True)
class QueryResult:
    """Normalized result from a query execution.

    Attributes:
        columns: Ordered metadata for each column in the result.
        rows: Raw row data as a list of dicts (column_name → value).
        row_count: Number of rows returned.
        execution_time_ms: How long the query took, in milliseconds.
        truncated: Whether the result was capped at the row limit.
        sql: The SQL that was actually executed.
    """

    columns: list[ColumnMetadata] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    truncated: bool = False
    sql: str = ""

    def to_json(self) -> list[dict[str, Any]]:
        """Export rows as JSON-serializable list of dicts.

        Handles types that aren't natively JSON-serializable:
        - datetime/date/time → ISO format strings
        - Decimal → float
        - bytes → hex string
        - UUID → string

        Returns:
            A list of dictionaries with JSON-safe values.
        """
        return [_serialize_row(row) for row in self.rows]

    def to_polars(self) -> Any:
        """Export rows as a Polars DataFrame.

        Returns:
            A ``polars.DataFrame`` built from the row data.

        Raises:
            ImportError: If Polars is not installed.
        """
        try:
            import polars as pl
        except ImportError as exc:
            raise ImportError(
                "Polars is required for to_polars(). Install it with: pip install polars"
            ) from exc

        if not self.rows:
            # Empty result — create schema-only DataFrame.
            schema = {col.name: pl.Utf8 for col in self.columns}
            return pl.DataFrame(schema=schema)

        return pl.DataFrame(self.to_json())

    def to_pandas(self) -> Any:
        """Export rows as a Pandas DataFrame.

        Returns:
            A ``pandas.DataFrame`` built from the row data.

        Raises:
            ImportError: If Pandas is not installed.
        """
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError(
                "Pandas is required for to_pandas(). Install it with: pip install pandas"
            ) from exc

        if not self.rows:
            return pd.DataFrame(columns=[col.name for col in self.columns])

        return pd.DataFrame(self.to_json())


def _serialize_value(value: Any) -> Any:
    """Convert a single value to a JSON-safe representation."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime | datetime.date | datetime.time):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, int | float | str | bool):
        return value
    # Fallback: stringify anything exotic (UUID, enums, etc.)
    return str(value)


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Serialize all values in a row dict."""
    return {k: _serialize_value(v) for k, v in row.items()}
