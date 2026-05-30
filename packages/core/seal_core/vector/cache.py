"""LRU cache for embedding vectors."""

from __future__ import annotations

import hashlib
from collections import OrderedDict


class EmbeddingCache:
    def __init__(self, max_size: int = 512) -> None:
        self._max_size = max_size
        self._cache: OrderedDict[str, list[float]] = OrderedDict()

    @staticmethod
    def key(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, text: str) -> list[float] | None:
        k = self.key(text)
        if k not in self._cache:
            return None
        self._cache.move_to_end(k)
        return self._cache[k]

    def set(self, text: str, embedding: list[float]) -> None:
        k = self.key(text)
        self._cache[k] = embedding
        self._cache.move_to_end(k)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)
