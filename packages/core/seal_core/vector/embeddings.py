"""LiteLLM embedding helpers."""

from __future__ import annotations

import asyncio

from litellm import aembedding

from seal_core.settings import get_settings
from seal_core.vector.cache import EmbeddingCache

_cache = EmbeddingCache()


def _embedding_model() -> str:
    model = get_settings().embedding_model
    if "/" not in model:
        return f"openai/{model}"
    return model


async def embed_text(text: str) -> list[float]:
    cached = _cache.get(text)
    if cached is not None:
        return cached
    response = await aembedding(model=_embedding_model(), input=[text])
    vector = response.data[0]["embedding"]
    _cache.set(text, vector)
    return vector


async def embed_texts(texts: list[str], *, max_concurrent: int | None = None) -> list[list[float]]:
    if not texts:
        return []
    settings = get_settings()
    sem_limit = max_concurrent or settings.rag_embed_max_concurrent
    sem = asyncio.Semaphore(sem_limit)

    async def _one(t: str) -> list[float]:
        async with sem:
            return await embed_text(t)

    return list(await asyncio.gather(*[_one(t) for t in texts]))
