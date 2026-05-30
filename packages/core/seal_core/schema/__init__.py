"""Schema introspection subpackage."""

from seal_core.schema.introspector import SchemaIntrospector, get_introspector
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

__all__ = [
    "ColumnInfo",
    "ColumnType",
    "ContinuousAggregateInfo",
    "DatabaseSchema",
    "HypertableInfo",
    "RelationshipInfo",
    "SchemaIntrospector",
    "TableKind",
    "TableSchema",
    "get_introspector",
]
