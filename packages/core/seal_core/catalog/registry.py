"""Load and query the data catalog YAML."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from seal_core.catalog.models import CatalogEntry, DataCatalog, catalog_entry_key
from seal_core.schema.models import DatabaseSchema, TableKind, TableSchema

logger = logging.getLogger(__name__)

_TABLE_KINDS = {TableKind.TABLE, TableKind.HYPERTABLE}
_VIEW_KINDS = {TableKind.VIEW, TableKind.MATERIALIZED_VIEW, TableKind.CONTINUOUS_AGGREGATE}


class DataCatalogRegistry:
    """In-memory registry backed by catalog YAML."""

    def __init__(self) -> None:
        self._catalog = DataCatalog()
        self._path: Path | None = None

    @property
    def catalog(self) -> DataCatalog:
        return self._catalog

    @property
    def path(self) -> Path | None:
        return self._path

    def load(self, path: str | Path) -> None:
        self._path = Path(path)
        if not self._path.is_file():
            self._catalog = DataCatalog()
            return
        with open(self._path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        if not raw:
            self._catalog = DataCatalog()
            return
        self._catalog = DataCatalog.model_validate(raw)

    def get_entry(self, name: str, schema_name: str = "public") -> CatalogEntry | None:
        key = catalog_entry_key(schema_name, name)
        for entry in self._catalog.tables:
            if catalog_entry_key(entry.schema_name, entry.name) == key:
                return entry
        return None

    def get_description(self, entry: CatalogEntry) -> str | None:
        return entry.description_for_kind()

    def validate_against_schema(self, schema: DatabaseSchema) -> list[str]:
        errors: list[str] = []
        schema_keys = {catalog_entry_key(t.schema_name, t.name) for t in schema.tables}
        for entry in self._catalog.tables:
            if catalog_entry_key(entry.schema_name, entry.name) not in schema_keys:
                errors.append(f"Unknown table in catalog: {entry.schema_name}.{entry.name}")
        return errors

    def to_prompt_context(self, table_names: list[str] | None = None) -> str:
        if not self._catalog.tables:
            return ""

        entries = self._catalog.tables
        if table_names:
            allowed = {n.lower() for n in table_names}
            entries = [e for e in entries if e.name.lower() in allowed]

        if not entries:
            return ""

        lines = ["\n## Data catalog (business context)\n"]
        for entry in entries:
            desc = self.get_description(entry)
            kind_label = entry.kind.value
            lines.append(f"### {entry.schema_name}.{entry.name} [{kind_label}]")
            if desc:
                lines.append(f"Description: {desc}")
            lines.append("")
        return "\n".join(lines)


def entry_from_table(table: TableSchema) -> CatalogEntry:
    from seal_core.catalog.models import CatalogColumn

    return CatalogEntry(
        schema=table.schema_name,
        name=table.name,
        kind=table.kind,
        columns=[
            CatalogColumn(
                name=c.name,
                data_type=c.data_type,
                normalized_type=c.normalized_type.value,
                nullable=c.nullable,
                is_primary_key=c.is_primary_key,
            )
            for c in table.columns
        ],
        table_description=table.description if table.kind in _TABLE_KINDS else None,
        view_description=table.description if table.kind in _VIEW_KINDS else None,
    )
