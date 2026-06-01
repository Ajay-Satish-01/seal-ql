"""Tests for EnhancementOrchestrator vector RAG availability."""

from __future__ import annotations

from seal_core.enhancement.orchestrator import EnhancementOrchestrator
from seal_core.enhancement.vector_rag import VectorRagEnhancer
from seal_core.vector.noop_store import NoopVectorStore


def test_vector_rag_available_false_for_noop_store() -> None:
    orchestrator = EnhancementOrchestrator([VectorRagEnhancer(NoopVectorStore())])
    assert orchestrator.vector_rag_available() is False


def test_vector_rag_available_true_without_vector_enhancer() -> None:
    orchestrator = EnhancementOrchestrator([])
    assert orchestrator.vector_rag_available() is True


def test_build_enhancement_metadata_no_vector_skip_without_vector_enhancer() -> None:
    from seal_core.pipeline.models import build_enhancement_metadata

    enh = build_enhancement_metadata(
        enabled=True,
        applied=["schema_aware"],
        database_id="default",
        vector_rag_available=True,
        orchestrator_available=True,
    )
    assert enh.vector_skipped_reason is None
