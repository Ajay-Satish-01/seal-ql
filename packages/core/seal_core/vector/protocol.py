"""Vendor-neutral vector store protocol."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field


class VectorDocument(BaseModel):
    id: str
    text: str
    metadata: dict[str, str] = Field(default_factory=dict)


class VectorStore(Protocol):
    async def upsert(
        self, documents: list[VectorDocument], embeddings: list[list[float]]
    ) -> None: ...

    async def search(self, query_embedding: list[float], *, top_k: int) -> list[VectorDocument]: ...

    async def delete_collection(self) -> None: ...
