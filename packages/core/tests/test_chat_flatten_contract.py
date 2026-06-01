"""Contract tests for chat JSON → seal.meta flatten (Python + golden file)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from seal_core.pipeline.models import build_stream_meta_event
from seal_core.pipeline.validate_metadata import (
    chat_response_to_stream_meta,
    validate_stream_meta_event,
)

_ROOT = Path(__file__).resolve().parents[3]
_GOLDEN_PATH = _ROOT / "tests" / "fixtures" / "chat_flatten_golden.json"


def _load_golden() -> dict[str, Any]:
    return json.loads(_GOLDEN_PATH.read_text())


def test_chat_flatten_golden_cases_match_python() -> None:
    data = _load_golden()
    for case in data["cases"]:
        flat = chat_response_to_stream_meta(case["response"])
        assert flat == case["expected_flat"], case["id"]
        assert not validate_stream_meta_event(flat), case["id"]


def test_golden_wire_format_cases_match_build_stream_meta_event() -> None:
    data = _load_golden()
    for case in data["cases"]:
        if not case.get("assert_matches_build"):
            continue
        build_args = case["build_args"]
        built = build_stream_meta_event(
            exec_result=None,
            results=None,
            columns=None,
            chart=None,
            **build_args,
        )
        flat = chat_response_to_stream_meta(case["response"])
        assert flat == built, case["id"]
        assert flat == case["expected_flat"], case["id"]


def test_chat_response_to_stream_meta_omits_absent_metadata_keys() -> None:
    flat = chat_response_to_stream_meta(
        {
            "session_id": "s-sparse",
            "metadata": {
                "used_sql": False,
                "refusal": True,
                "enhancement": {"enabled": False, "applied": []},
            },
        }
    )
    assert "database_id" not in flat
    assert flat["refusal"] is True
    assert not validate_stream_meta_event(flat)
