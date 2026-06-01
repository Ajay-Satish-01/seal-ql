"""Cross-check stream meta validation and metadata key contract."""

from __future__ import annotations

import json
from pathlib import Path

from seal_core.pipeline.validate_metadata import (
    EXECUTION_META_KEYS,
    STREAM_META_METADATA_KEYS,
    validate_stream_meta_event,
)

_ROOT = Path(__file__).resolve().parents[3]
_KEYS_PATH = _ROOT / "config" / "stream_meta_metadata_keys.json"
_MATRIX_PATH = _ROOT / "tests" / "fixtures" / "stream_meta_validation_matrix.json"


def test_stream_meta_metadata_keys_match_fixture() -> None:
    expected = tuple(json.loads(_KEYS_PATH.read_text()))
    assert expected == STREAM_META_METADATA_KEYS
    assert frozenset(expected[:7]) == EXECUTION_META_KEYS


def test_stream_meta_validation_matrix_python() -> None:
    data = json.loads(_MATRIX_PATH.read_text())
    for case in data["cases"]:
        errors = validate_stream_meta_event(case["payload"])
        passed = not errors
        assert passed == case["should_pass"], f"{case['id']}: {errors}"
