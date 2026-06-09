"""Live E2E tests for layered reasoning and clarification (HTTP against running API).

Requires `make up` with seeded data and a working LLM. Tests skip with a warning
when the provider returns 429, timeouts, or model-unavailable errors.
"""

from __future__ import annotations

import warnings

import httpx
import pytest
from tests.e2e_llm_helpers import (
    assert_chat_response_ok,
    assert_no_schema_table_clarification,
    assert_not_refusal,
    assert_query_response_ok,
    post_chat_json,
    probe_live_chat,
    probe_live_llm,
    skip_if_llm_unavailable,
)
from tests.shared import LIVE_API_KEY, live_api_headers

pytest_plugins = ["tests.live_http_fixtures"]

_CLARIFICATION_ASSISTANT = (
    "**A few details would help**\n"
    "- What time range should I use?\n"
    "- What minimum threshold should I apply?"
)


@pytest.fixture(scope="module")
def llm_ready() -> None:
    """Skip the module when neither chat nor query can reach a healthy LLM path."""
    from tests.live_http_fixtures import api_base_url

    base = api_base_url()
    chat_reason = probe_live_chat(base_url=base, api_key=LIVE_API_KEY, timeout=180.0)
    query_reason = probe_live_llm(base_url=base, api_key=LIVE_API_KEY, timeout=180.0)
    if chat_reason is not None and query_reason is not None:
        pytest.skip(f"LLM unavailable (chat: {chat_reason}; query: {query_reason})")


def test_e2e_chat_clarification_follow_up_stays_in_scope(
    llm_ready: None,
    live_http_llm: httpx.Client,
    catalog_table_name: str,
) -> None:
    """Short entity replies after clarification must stay in-scope and avoid schema prompts."""
    headers = live_api_headers()
    body = assert_chat_response_ok(
        post_chat_json(
            live_http_llm,
            message=catalog_table_name,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Rank rows in the {catalog_table_name} table by total quantity "
                        "across all available history."
                    ),
                },
                {"role": "assistant", "content": _CLARIFICATION_ASSISTANT},
            ],
            headers=headers,
        )
    )
    assert_not_refusal(body)
    assert_no_schema_table_clarification(body)


def test_e2e_chat_multi_turn_clarification_no_schema_prompt(
    llm_ready: None,
    live_http_llm: httpx.Client,
    catalog_table_name: str,
) -> None:
    """Organic multi-turn clarification must not ask users to pick schema tables."""
    headers = live_api_headers()

    turn1 = assert_chat_response_ok(
        post_chat_json(
            live_http_llm,
            message=(f"Rank {catalog_table_name} records by total quantity across all history."),
            headers=headers,
        )
    )
    if (turn1.get("metadata") or {}).get("refusal"):
        warnings.warn(
            "Organic multi-turn test skipped: model refused a data-native ranking prompt",
            UserWarning,
            stacklevel=1,
        )
        pytest.skip("Model refused data-native ranking prompt on turn 1")
    assert_not_refusal(turn1)
    assert_no_schema_table_clarification(turn1)
    session_id = turn1["session_id"]

    turn2 = assert_chat_response_ok(
        post_chat_json(
            live_http_llm,
            message="Use all available history and apply a minimum quantity threshold of 500.",
            session_id=session_id,
            headers=headers,
        )
    )
    assert_not_refusal(turn2)
    assert_no_schema_table_clarification(turn2)

    turn3 = assert_chat_response_ok(
        post_chat_json(
            live_http_llm,
            message=catalog_table_name,
            session_id=session_id,
            headers=headers,
        )
    )
    assert_not_refusal(turn3)
    assert_no_schema_table_clarification(turn3)


def test_e2e_chat_vague_analytics_no_schema_table_prompt(
    llm_ready: None,
    live_http_llm: httpx.Client,
) -> None:
    """Vague analytics prompts must not ask the user to pick a schema table."""
    headers = live_api_headers()
    body = assert_chat_response_ok(
        post_chat_json(
            live_http_llm,
            message="Show me an overview of performance metrics in the database.",
            headers=headers,
        )
    )
    assert_not_refusal(body)
    assert_no_schema_table_clarification(body)


def test_e2e_query_clarification_no_schema_table_prompt(
    llm_ready: None,
    live_http_llm: httpx.Client,
) -> None:
    """Query-route clarification must not delegate table selection to the user."""
    headers = live_api_headers()
    try:
        response = live_http_llm.post(
            "/v1/query",
            json={"query": "show me trends"},
            headers=headers,
        )
    except httpx.RequestError as exc:
        skip_if_llm_unavailable(exc=exc)
        raise

    body = assert_query_response_ok(response)
    assert_no_schema_table_clarification(body)
