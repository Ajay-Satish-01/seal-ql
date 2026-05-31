"""Persist in-memory catalog registry to YAML (description write-through)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import yaml

from seal_core.catalog.models import DataCatalog

if TYPE_CHECKING:
    from pathlib import Path

    from seal_core.catalog.registry import DataCatalogRegistry

logger = logging.getLogger(__name__)


def persist_catalog_descriptions(registry: DataCatalogRegistry, catalog_path: Path) -> None:
    """Write current registry catalog to YAML (atomic replace)."""
    cat = registry.catalog
    out = DataCatalog(
        version=cat.version,
        generated_at=cat.generated_at,
        schema_hash=cat.schema_hash,
        tables=list(cat.tables),
    )
    tmp = catalog_path.with_suffix(".yaml.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            out.model_dump(by_alias=True, mode="json", exclude_none=True),
            f,
            default_flow_style=False,
            sort_keys=False,
        )
    tmp.replace(catalog_path)
    logger.info("Wrote catalog descriptions to %s", catalog_path)
