"""No-op vector store when RAG is disabled."""

from seal_core.vector.protocol import VectorDocument


class NoopVectorStore:
    async def upsert(self, documents: list[VectorDocument], embeddings: list[list[float]]) -> None:
        return None

    async def search(self, query_embedding: list[float], *, top_k: int) -> list[VectorDocument]:
        return []

    async def delete_collection(self) -> None:
        return None
