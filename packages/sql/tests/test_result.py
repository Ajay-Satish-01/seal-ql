"""Tests for the QueryResult module."""

from __future__ import annotations

import datetime
import decimal

import pytest
from intelligence_sql.result import ColumnMetadata, QueryResult, _serialize_value

# ---------------------------------------------------------------------------
# ColumnMetadata
# ---------------------------------------------------------------------------


class TestColumnMetadata:
    """Tests for the ColumnMetadata dataclass."""

    def test_basic_creation(self) -> None:
        col = ColumnMetadata(name="id", type="int4", nullable=False)
        assert col.name == "id"
        assert col.type == "int4"
        assert col.nullable is False

    def test_defaults(self) -> None:
        col = ColumnMetadata(name="x")
        assert col.type == "str"
        assert col.nullable is True

    def test_frozen(self) -> None:
        col = ColumnMetadata(name="x")
        with pytest.raises(AttributeError):
            col.name = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# QueryResult — basic properties
# ---------------------------------------------------------------------------


class TestQueryResultBasic:
    """Tests for basic QueryResult properties and defaults."""

    def test_empty_result(self) -> None:
        result = QueryResult()
        assert result.columns == []
        assert result.rows == []
        assert result.row_count == 0
        assert result.execution_time_ms == 0.0
        assert result.truncated is False
        assert result.sql == ""

    def test_populated_result(self) -> None:
        columns = [
            ColumnMetadata(name="id", type="int4"),
            ColumnMetadata(name="name", type="text"),
        ]
        rows = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        result = QueryResult(
            columns=columns,
            rows=rows,
            row_count=2,
            execution_time_ms=12.5,
            truncated=False,
            sql="SELECT id, name FROM users",
        )
        assert result.row_count == 2
        assert result.execution_time_ms == 12.5
        assert result.sql == "SELECT id, name FROM users"
        assert result.truncated is False

    def test_frozen(self) -> None:
        result = QueryResult()
        with pytest.raises(AttributeError):
            result.row_count = 10  # type: ignore[misc]


# ---------------------------------------------------------------------------
# to_json
# ---------------------------------------------------------------------------


class TestToJson:
    """Tests for QueryResult.to_json()."""

    def test_empty_rows(self) -> None:
        result = QueryResult(rows=[])
        assert result.to_json() == []

    def test_simple_types(self) -> None:
        rows = [{"id": 1, "name": "Alice", "active": True, "score": 3.14}]
        result = QueryResult(rows=rows)
        json_rows = result.to_json()
        assert json_rows == [{"id": 1, "name": "Alice", "active": True, "score": 3.14}]

    def test_none_values(self) -> None:
        rows = [{"id": 1, "email": None}]
        result = QueryResult(rows=rows)
        json_rows = result.to_json()
        assert json_rows[0]["email"] is None

    def test_datetime_serialization(self) -> None:
        dt = datetime.datetime(2025, 6, 15, 10, 30, 0)
        rows = [{"ts": dt}]
        result = QueryResult(rows=rows)
        json_rows = result.to_json()
        assert json_rows[0]["ts"] == "2025-06-15T10:30:00"

    def test_date_serialization(self) -> None:
        d = datetime.date(2025, 6, 15)
        rows = [{"day": d}]
        result = QueryResult(rows=rows)
        json_rows = result.to_json()
        assert json_rows[0]["day"] == "2025-06-15"

    def test_time_serialization(self) -> None:
        t = datetime.time(14, 30, 0)
        rows = [{"t": t}]
        result = QueryResult(rows=rows)
        json_rows = result.to_json()
        assert json_rows[0]["t"] == "14:30:00"

    def test_decimal_serialization(self) -> None:
        rows = [{"amount": decimal.Decimal("123.45")}]
        result = QueryResult(rows=rows)
        json_rows = result.to_json()
        assert json_rows[0]["amount"] == 123.45
        assert isinstance(json_rows[0]["amount"], float)

    def test_bytes_serialization(self) -> None:
        rows = [{"data": b"\xde\xad\xbe\xef"}]
        result = QueryResult(rows=rows)
        json_rows = result.to_json()
        assert json_rows[0]["data"] == "deadbeef"

    def test_exotic_type_serialization(self) -> None:
        """Types we don't explicitly handle get str()-ified."""
        import uuid

        uid = uuid.uuid4()
        rows = [{"uid": uid}]
        result = QueryResult(rows=rows)
        json_rows = result.to_json()
        assert json_rows[0]["uid"] == str(uid)

    def test_multiple_rows(self) -> None:
        rows = [
            {"id": 1, "val": decimal.Decimal("10.5")},
            {"id": 2, "val": decimal.Decimal("20.0")},
            {"id": 3, "val": None},
        ]
        result = QueryResult(rows=rows)
        json_rows = result.to_json()
        assert len(json_rows) == 3
        assert json_rows[0]["val"] == 10.5
        assert json_rows[2]["val"] is None


# ---------------------------------------------------------------------------
# to_polars
# ---------------------------------------------------------------------------


class TestToPolars:
    """Tests for QueryResult.to_polars()."""

    def test_basic_dataframe(self) -> None:
        import polars as pl

        columns = [
            ColumnMetadata(name="id", type="int4"),
            ColumnMetadata(name="name", type="text"),
        ]
        rows = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        result = QueryResult(columns=columns, rows=rows, row_count=2)
        df = result.to_polars()

        assert isinstance(df, pl.DataFrame)
        assert df.shape == (2, 2)
        assert df.columns == ["id", "name"]
        assert df["id"].to_list() == [1, 2]
        assert df["name"].to_list() == ["Alice", "Bob"]

    def test_empty_result(self) -> None:
        import polars as pl

        columns = [
            ColumnMetadata(name="id"),
            ColumnMetadata(name="name"),
        ]
        result = QueryResult(columns=columns, rows=[], row_count=0)
        df = result.to_polars()

        assert isinstance(df, pl.DataFrame)
        assert df.shape == (0, 2)

    def test_serialized_types(self) -> None:
        """Polars export should use JSON-serialized values (e.g., dates as strings)."""
        import polars as pl

        rows = [{"ts": datetime.datetime(2025, 1, 1, 12, 0, 0), "amt": decimal.Decimal("99.99")}]
        columns = [ColumnMetadata(name="ts"), ColumnMetadata(name="amt")]
        result = QueryResult(columns=columns, rows=rows, row_count=1)
        df = result.to_polars()

        assert isinstance(df, pl.DataFrame)
        assert df.shape == (1, 2)


# ---------------------------------------------------------------------------
# to_pandas
# ---------------------------------------------------------------------------


class TestToPandas:
    """Tests for QueryResult.to_pandas()."""

    def test_basic_dataframe(self) -> None:
        pd = pytest.importorskip("pandas")

        columns = [
            ColumnMetadata(name="id", type="int4"),
            ColumnMetadata(name="name", type="text"),
        ]
        rows = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        result = QueryResult(columns=columns, rows=rows, row_count=2)
        df = result.to_pandas()

        assert isinstance(df, pd.DataFrame)
        assert df.shape == (2, 2)
        assert list(df.columns) == ["id", "name"]
        assert df["id"].tolist() == [1, 2]

    def test_empty_result(self) -> None:
        pd = pytest.importorskip("pandas")

        columns = [
            ColumnMetadata(name="id"),
            ColumnMetadata(name="name"),
        ]
        result = QueryResult(columns=columns, rows=[], row_count=0)
        df = result.to_pandas()

        assert isinstance(df, pd.DataFrame)
        assert df.shape == (0, 2)
        assert list(df.columns) == ["id", "name"]


# ---------------------------------------------------------------------------
# _serialize_value edge cases
# ---------------------------------------------------------------------------


class TestSerializeValue:
    """Tests for the _serialize_value helper."""

    def test_none(self) -> None:
        assert _serialize_value(None) is None

    def test_int(self) -> None:
        assert _serialize_value(42) == 42

    def test_float(self) -> None:
        assert _serialize_value(3.14) == 3.14

    def test_str(self) -> None:
        assert _serialize_value("hello") == "hello"

    def test_bool(self) -> None:
        assert _serialize_value(True) is True
        assert _serialize_value(False) is False

    def test_datetime_with_tz(self) -> None:
        dt = datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC)
        result = _serialize_value(dt)
        assert "2025-01-01" in result
        assert "+00:00" in result

    def test_decimal_precision(self) -> None:
        # Decimal with many digits — should become a float.
        d = decimal.Decimal("1.123456789012345")
        result = _serialize_value(d)
        assert isinstance(result, float)
