"""Load VectorStore from settings."""

from __future__ import annotations

import importlib
import json
import logging
from typing import TYPE_CHECKING

from seal_core.settings import Settings, get_settings
from seal_core.vector.noop_store import NoopVectorStore

if TYPE_CHECKING:
    from seal_core.vector.protocol import VectorStore

logger = logging.getLogger(__name__)

_CHROMA_INSTALL_HINT = (
    "Chroma is not installed. Either set VECTOR_STORE=none, or install the optional extra:\n"
    "  Local:  uv sync --package seal-core --extra chroma\n"
    "  Docker: set SEAL_EXTRA=chroma in .env (or pass --build-arg SEAL_EXTRA=chroma) and rebuild"
)


def chroma_is_available() -> bool:
    """True when the chromadb package is importable."""
    try:
        import chromadb  # noqa: F401
    except ImportError:
        return False
    return True


def _load_class(dotted: str) -> type:
    module_path, _, class_name = dotted.rpartition(".")
    if not module_path:
        raise ValueError(f"Invalid VECTOR_STORE_CLASS: {dotted}")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def get_vector_store(settings: Settings | None = None) -> VectorStore:
    settings = settings or get_settings()

    if settings.vector_store_class:
        config = {}
        if settings.vector_store_config:
            try:
                config = json.loads(settings.vector_store_config)
            except json.JSONDecodeError as e:
                raise ValueError(
                    "VECTOR_STORE_CONFIG must be valid JSON; got "
                    f"{settings.vector_store_config!r}: {e}"
                ) from e
        try:
            cls = _load_class(settings.vector_store_class)
            return cls(**config)  # type: ignore[no-any-return]
        except (ImportError, AttributeError, TypeError, ValueError) as e:
            raise RuntimeError(
                f"Failed to load VECTOR_STORE_CLASS={settings.vector_store_class!r}: {e}"
            ) from e

    if settings.vector_store.lower() == "none":
        return NoopVectorStore()

    if settings.vector_store.lower() == "chroma":
        if not chroma_is_available():
            raise ImportError(_CHROMA_INSTALL_HINT)
        from seal_core.vector.chroma_store import ChromaVectorStore

        return ChromaVectorStore(persist_path=settings.chroma_persist_path)

    logger.warning("Unknown VECTOR_STORE=%s, using noop", settings.vector_store)
    return NoopVectorStore()
