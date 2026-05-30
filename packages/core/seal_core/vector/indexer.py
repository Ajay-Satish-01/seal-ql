"""Build vector index from schema, catalog, and optional documents."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from seal_core.settings import get_settings
from seal_core.vector.embeddings import embed_texts
from seal_core.vector.protocol import VectorDocument, VectorStore

if TYPE_CHECKING:
    from seal_core.catalog.registry import DataCatalogRegistry
    from seal_core.schema.models import DatabaseSchema

logger = logging.getLogger(__name__)


def _chunk_sources(
    schema: DatabaseSchema,
    catalog: DataCatalogRegistry | None,
    documents_path: str | None,
) -> list[VectorDocument]:
    docs: list[VectorDocument] = []

    if catalog is not None:
        for entry in catalog.catalog.tables:
            desc = catalog.get_description(entry)
            parts = [f"{entry.schema_name}.{entry.name} ({entry.kind.value})"]
            if desc:
                parts.append(desc)
            text = " ".join(parts)
            docs.append(
                VectorDocument(
                    id=f"catalog:{entry.schema_name}.{entry.name}",
                    text=text,
                    metadata={
                        "source": "catalog",
                        "table": entry.name,
                        "schema": entry.schema_name,
                    },
                )
            )

    for table in schema.tables:
        if table.description:
            docs.append(
                VectorDocument(
                    id=f"schema:{table.schema_name}.{table.name}",
                    text=f"{table.schema_name}.{table.name}: {table.description}",
                    metadata={"source": "schema", "table": table.name},
                )
            )
        for col in table.columns:
            if col.description:
                docs.append(
                    VectorDocument(
                        id=f"schema:{table.schema_name}.{table.name}.{col.name}",
                        text=f"{table.name}.{col.name}: {col.description}",
                        metadata={"source": "schema_column", "table": table.name},
                    )
                )

    if documents_path:
        root = Path(documents_path)
        if root.is_dir():
            for path in root.rglob("*"):
                if path.suffix.lower() in {".md", ".txt", ".yaml", ".yml"}:
                    try:
                        text = path.read_text(encoding="utf-8")[:8000]
                        docs.append(
                            VectorDocument(
                                id=f"doc:{path.name}",
                                text=text,
                                metadata={"source": "document", "path": str(path)},
                            )
                        )
                    except OSError as e:
                        logger.warning("Skip document %s: %s", path, e)

    return docs


class VectorIndexBuilder:
    def __init__(self, store: VectorStore) -> None:
        self._store = store

    async def build(
        self,
        schema: DatabaseSchema,
        catalog: DataCatalogRegistry | None = None,
    ) -> int:
        settings = get_settings()
        if settings.vector_store.lower() == "none" and not settings.vector_store_class:
            return 0

        documents = _chunk_sources(schema, catalog, settings.rag_documents_path)
        if not documents:
            return 0

        batch_size = settings.rag_embed_batch_size
        await self._store.delete_collection()
        total = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            embeddings = await embed_texts([d.text for d in batch])
            await self._store.upsert(batch, embeddings)
            total += len(batch)
        logger.info("Indexed %s documents into vector store", total)
        return total
