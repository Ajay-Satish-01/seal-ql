"""Ensure Settings fields align with documented .env.example variables."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from seal_core.settings import Settings, settings_env_names


def _find_env_example() -> Path:
    """Locate repo-root .env.example (works locally and in Docker with a bind mount)."""
    start = Path(__file__).resolve().parent
    for directory in (start, *start.parents):
        candidate = directory / ".env.example"
        if candidate.is_file():
            return candidate
    pytest.fail(
        "Could not find .env.example — mount repo root in Docker "
        "(see docker-compose.yml: ./.env.example:/app/.env.example)"
    )


_ENV_EXAMPLE = _find_env_example()

# Build-only / compose-only keys (not Pydantic Settings fields)
_NON_SETTINGS_ENV = frozenset(
    {
        "COMPOSE_PROFILES",
        "SEAL_EXTRA",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "POSTGRES_PORT",
    }
)


def _env_keys_in_line(line: str) -> set[str]:
    """Extract KEY from KEY= assignments (active or commented, e.g. # FOO=bar)."""
    return set(re.findall(r"([A-Z][A-Z0-9_]*)=", line))


def _parse_env_example_keys(path: Path) -> set[str]:
    """Uncommented KEY= lines only (values loaded from .env)."""
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        keys.update(_env_keys_in_line(stripped))
    return keys


def _all_documented_env_keys(path: Path) -> set[str]:
    """Every KEY= mentioned in .env.example (including commented templates)."""
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        keys.update(_env_keys_in_line(line))
    return keys


def test_env_example_keys_are_known_settings() -> None:
    """Every active KEY= in .env.example maps to Settings (or documented compose-only)."""
    example_keys = _parse_env_example_keys(_ENV_EXAMPLE)
    known = set(settings_env_names()) | _NON_SETTINGS_ENV
    unknown = example_keys - known
    assert not unknown, f".env.example keys not in Settings: {sorted(unknown)}"


def test_settings_fields_documented_in_env_example() -> None:
    """Every Settings env name appears in .env.example (comment or assignment)."""
    documented = _all_documented_env_keys(_ENV_EXAMPLE)
    missing = [name for name in settings_env_names() if name not in documented]
    assert not missing, f"Settings env vars missing from .env.example: {missing}"


def test_empty_optional_strings_become_none() -> None:
    settings = Settings(
        semantic_directory="",
        rag_documents_path="  ",
        seal_enhancers="",
        _env_file=None,
    )
    assert settings.semantic_directory is None
    assert settings.rag_documents_path is None
    assert settings.seal_enhancers is None


def test_vector_store_normalizes() -> None:
    settings = Settings(vector_store=" Chroma ", _env_file=None)
    assert settings.vector_store == "chroma"
