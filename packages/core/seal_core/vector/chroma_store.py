"""ChromaDB reference VectorStore implementation (requires chromadb package)."""

from __future__ import annotations

try:
    import chromadb
except ImportError as e:
    raise ImportError(
        "chromadb is not installed. pip install 'chromadb>=0.5.23,<0.6' or set VECTOR_STORE=none"
    ) from e

from seal_core.vector.protocol import VectorDocument


class ChromaVectorStore:
    def __init__(self, persist_path: str, collection_name: str = "seal_rag") -> None:
        self._client = chromadb.PersistentClient(path=persist_path)
        self._collection = self._client.get_or_create_collection(name=collection_name)

    async def upsert(self, documents: list[VectorDocument], embeddings: list[list[float]]) -> None:
        if not documents:
            return
        self._collection.upsert(
            ids=[d.id for d in documents],
            documents=[d.text for d in documents],
            embeddings=embeddings,
            metadatas=[d.metadata for d in documents],
        )

    async def search(self, query_embedding: list[float], *, top_k: int) -> list[VectorDocument]:
        result = self._collection.query(query_embeddings=[query_embedding], n_results=top_k)
        docs: list[VectorDocument] = []
        ids = result.get("ids") or [[]]
        texts = result.get("documents") or [[]]
        metas = result.get("metadatas") or [[]]
        if not ids or not ids[0]:
            return docs
        for i, doc_id in enumerate(ids[0]):
            text = texts[0][i] if texts and texts[0] else ""
            meta = metas[0][i] if metas and metas[0] and metas[0][i] else {}
            docs.append(
                VectorDocument(
                    id=doc_id,
                    text=text or "",
                    metadata={str(k): str(v) for k, v in (meta or {}).items()},
                )
            )
        return docs

    async def delete_collection(self) -> None:
        name = self._collection.name
        self._client.delete_collection(name)
