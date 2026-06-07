"""Orchestrates pluggable reasoning layers for chat and query routes."""

from __future__ import annotations

import logging
import time
from dataclasses import replace
from typing import TYPE_CHECKING

from seal_core.reasoning.config import ReasoningConfig, resolve_reasoning_config
from seal_core.reasoning.layers import (
    AnalysisFollowupsLayer,
    ClarificationLayer,
    InferredContextLayer,
    ResearchNotesLayer,
)
from seal_core.reasoning.merge import merge_reasoning_metadata
from seal_core.reasoning.models import (
    ReasoningContext,
    ReasoningLayerResult,
    ReasoningMetadata,
    ReasoningPhase,
    merge_reasoning_results,
)
from seal_core.reasoning.telemetry import record_reasoning_phase
from seal_core.settings import get_settings

if TYPE_CHECKING:
    from seal_core.reasoning.protocol import ReasoningLayer

logger = logging.getLogger(__name__)


def _latency_budget_ms() -> float | None:
    budget = get_settings().reasoning_latency_budget_ms
    return float(budget) if budget > 0 else None


class ReasoningOrchestrator:
    """Run registered reasoning layers for a phase and merge outputs."""

    def __init__(
        self,
        layers: list[ReasoningLayer] | None = None,
        *,
        config: ReasoningConfig | None = None,
    ) -> None:
        self._layers = list(layers or [])
        self._config = config

    def register(self, layer: ReasoningLayer) -> None:
        """Add a custom reasoning layer at runtime."""
        self._layers.append(layer)

    def _resolve_config(self, route: str) -> ReasoningConfig:
        return self._config or resolve_reasoning_config(route)

    def _layers_for_phase(self, phase: ReasoningPhase) -> list[ReasoningLayer]:
        return [layer for layer in self._layers if layer.phase == phase]

    async def _execute_layers(
        self,
        layers: list[ReasoningLayer],
        ctx: ReasoningContext,
        *,
        phase_label: str,
    ) -> ReasoningMetadata:
        """Run a list of layers with fail-open semantics, budget enforcement, and telemetry."""
        results: list[ReasoningLayerResult] = []
        budget_ms = _latency_budget_ms()
        phase_started = time.perf_counter()

        for layer in layers:
            if not layer.enabled(ctx):
                continue
            layer_name = getattr(layer, "name", "unknown")
            if budget_ms is not None and budget_ms <= 0:
                results.append(
                    ReasoningLayerResult(
                        layer_name=layer_name,
                        unavailable_reason="latency_budget_exceeded",
                    )
                )
                continue
            started = time.perf_counter()
            try:
                result = await layer.run(ctx)
                results.append(result)
            except Exception as exc:
                logger.warning("reasoning layer %s failed: %s", layer_name, exc)
                results.append(
                    ReasoningLayerResult(
                        layer_name=layer_name,
                        unavailable_reason="layer_error",
                    )
                )
            if budget_ms is not None:
                budget_ms -= (time.perf_counter() - started) * 1000

        merged = merge_reasoning_results(results)
        elapsed_ms = (time.perf_counter() - phase_started) * 1000
        record_reasoning_phase(
            route=ctx.route,
            phase=phase_label,
            layers_applied=merged.layers_applied,
            clarification_required=merged.clarification_required,
            layer_failures=merged.layers_unavailable,
            elapsed_ms=elapsed_ms,
        )
        logger.debug(
            "reasoning phase=%s route=%s applied=%s clarification=%s",
            phase_label,
            ctx.route,
            merged.layers_applied,
            merged.clarification_required,
        )
        return merged

    async def run_phase(
        self,
        ctx: ReasoningContext,
        phase: ReasoningPhase,
    ) -> ReasoningMetadata:
        """Execute all enabled layers for a phase with fail-open semantics."""
        config = self._resolve_config(ctx.route)
        if not config.enabled:
            return ReasoningMetadata()

        phase_ctx = replace(ctx, phase=phase)
        layers = self._layers_for_phase(phase)
        return await self._execute_layers(layers, phase_ctx, phase_label=phase.value)

    async def run_pre(self, ctx: ReasoningContext) -> ReasoningMetadata:
        """Pre-execution reasoning (clarification, inferred context)."""
        return await self.run_phase(ctx, ReasoningPhase.PRE_EXECUTION)

    async def run_post(self, ctx: ReasoningContext) -> ReasoningMetadata:
        """Post-execution reasoning (follow-ups, research notes)."""
        return await self.run_phase(ctx, ReasoningPhase.POST_EXECUTION)

    async def run_clarification_only(self, ctx: ReasoningContext) -> ReasoningMetadata:
        """Run only the clarification layer (e.g. after schema introspection)."""
        config = self._resolve_config(ctx.route)
        if not config.enabled or not config.clarification_enabled:
            return ReasoningMetadata()

        phase_ctx = replace(ctx, phase=ReasoningPhase.PRE_EXECUTION)
        clarification_layers = [
            layer
            for layer in self._layers_for_phase(ReasoningPhase.PRE_EXECUTION)
            if getattr(layer, "name", "") == "clarification"
        ]
        return await self._execute_layers(
            clarification_layers,
            phase_ctx,
            phase_label="pre_execution:clarification_only",
        )

    async def run_full(
        self,
        ctx: ReasoningContext,
        *,
        include_post: bool,
    ) -> ReasoningMetadata:
        """Run pre phase and optionally merge post phase results."""
        pre = await self.run_pre(ctx)
        if not include_post:
            return pre
        post = await self.run_post(ctx)
        return merge_reasoning_metadata(pre, post)


def build_default_orchestrator() -> ReasoningOrchestrator:
    """Construct the default reasoning layer chain."""
    return ReasoningOrchestrator(
        layers=[
            InferredContextLayer(),
            ClarificationLayer(),
            AnalysisFollowupsLayer(),
            ResearchNotesLayer(),
        ],
    )
