"""Lightweight reasoning telemetry for rollout observability."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def record_reasoning_phase(
    *,
    route: str,
    phase: str,
    layers_applied: list[str],
    clarification_required: bool,
    layer_failures: dict[str, str],
    elapsed_ms: float,
) -> None:
    """Emit structured reasoning counters (scrapable from logs)."""
    payload: dict[str, Any] = {
        "event": "reasoning.phase",
        "route": route,
        "phase": phase,
        "layers_applied": layers_applied,
        "clarification_required": clarification_required,
        "layer_failures": layer_failures,
        "elapsed_ms": round(elapsed_ms, 2),
    }
    logger.info("reasoning.telemetry %s", payload)
