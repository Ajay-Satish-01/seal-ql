"""Pydantic models for the auto-generated data catalog."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from seal_core.schema.models import TableKind


class CatalogColumn(BaseModel):
    name: str
    data_type: str
    normalized_type: str
    nullable: bool = True
    is_primary_key: bool = False


class CatalogEntry(BaseModel):
    schema_name: str = Field(default="public", alias="schema")
    name: str
    kind: TableKind = TableKind.TABLE
    columns: list[CatalogColumn] = Field(default_factory=list)
    table_description: str | None = None
    view_description: str | None = None

    model_config = {"populate_by_name": True}

    def description_for_kind(self) -> str | None:
        view_kinds = (
            TableKind.VIEW,
            TableKind.MATERIALIZED_VIEW,
            TableKind.CONTINUOUS_AGGREGATE,
        )
        if self.kind in view_kinds:
            return self.view_description
        return self.table_description


class DataCatalog(BaseModel):
    version: int = 1
    generated_at: str | None = None
    schema_hash: str | None = None
    tables: list[CatalogEntry] = Field(default_factory=list)


class CatalogSyncResult(BaseModel):
    added: int = 0
    updated: int = 0
    preserved: int = 0
    removed: int = 0
    path: str = ""


def catalog_entry_key(schema_name: str, name: str) -> tuple[str, str]:
    return (schema_name.lower(), name.lower())


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
