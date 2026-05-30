import pytest
from seal_core.settings import Settings
from seal_core.vector.factory import chroma_is_available, get_vector_store
from seal_core.vector.noop_store import NoopVectorStore


def test_vector_store_none() -> None:
    settings = Settings(vector_store="none", _env_file=None)
    store = get_vector_store(settings)
    assert isinstance(store, NoopVectorStore)


def test_vector_store_chroma_without_deps_raises() -> None:
    if chroma_is_available():
        pytest.skip("chromadb is installed in this environment")
    settings = Settings(vector_store="chroma", _env_file=None)
    with pytest.raises(ImportError, match="VECTOR_STORE=none"):
        get_vector_store(settings)


def test_validate_vector_store_chroma_without_deps() -> None:
    if chroma_is_available():
        pytest.skip("chromadb is installed in this environment")
    settings = Settings(vector_store="chroma", _env_file=None)
    errors = settings.collect_vector_store_configuration_errors()
    assert len(errors) == 1
    assert "chromadb" in errors[0]


def test_validate_vector_store_none_ok() -> None:
    settings = Settings(vector_store="none", _env_file=None)
    assert settings.collect_vector_store_configuration_errors() == []
