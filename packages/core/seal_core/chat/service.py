"""Chat orchestration service."""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

import litellm
from seal_charts.engine import ChartEngine

from seal_core.catalog.table_names import catalog_table_names, merge_table_name_hints
from seal_core.chat.errors import SessionDatabaseMismatchError
from seal_core.chat.explainability import ChatMessageExplainability
from seal_core.chat.models import ChatAnswer, ChatAnswerEnrichment, ChatDecision, ChatMessage
from seal_core.chat.prompts import (
    CHAT_ANSWER_ENRICHMENT_SYSTEM,
    CHAT_ANSWER_SYSTEM,
    CHAT_DECISION_SYSTEM,
)
from seal_core.chat.retriever import ContextRetriever
from seal_core.chat.sse import format_openai_sse_delta
from seal_core.database.config import DEFAULT_DATABASE_ID, planner_resources_for_database
from seal_core.database.registry import UnknownDatabaseError
from seal_core.enhancement.context import EnhancementContext
from seal_core.guardrails.models import ScopeMetadata, ScopeResult
from seal_core.guardrails.prompts import LIMIT_REFUSAL_MESSAGE, REFUSAL_SYSTEM
from seal_core.guardrails.scope import classify_scope
from seal_core.guardrails.suggestions import merge_suggestions, suggest_queries
from seal_core.intent import content_for_llm_history, effective_user_message
from seal_core.llm.client import get_api_base, get_api_key, get_async_client, get_model
from seal_core.llm.http_errors import llm_http_error, llm_stream_error_sse
from seal_core.pipeline.execute import ExecuteQueryResult, execute_natural_language_query
from seal_core.pipeline.models import build_chat_metadata, build_stream_meta_event
from seal_core.pipeline.provenance import build_catalog_matches
from seal_core.pipeline.trust import (
    apply_trust_gating_to_chat_response,
    apply_trust_gating_to_stream_meta,
    is_trust_explainability_enabled,
)
from seal_core.pipeline.validate_metadata import (
    enforce_nested_chat_metadata,
    enforce_stream_meta_validation,
)
from seal_core.reasoning.clarification_response import clarification_message
from seal_core.reasoning.merge import merge_answer_reasoning, merge_reasoning_metadata
from seal_core.reasoning.models import (
    DatabaseCapabilities,
    ReasoningContext,
    ReasoningMetadata,
    ReasoningPhase,
    append_reasoning_to_message,
    normalize_reasoning_clarification,
    reasoning_suffix_delta,
    should_return_clarification,
)
from seal_core.reasoning.orchestrator import build_default_orchestrator
from seal_core.serialization import safe_json_dumps
from seal_core.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from seal_core.chat.session.base import BaseSessionStore
    from seal_core.database.registry import DatabaseRegistry
    from seal_core.enhancement.orchestrator import EnhancementOrchestrator
    from seal_core.planner.planner import QueryPlanner
    from seal_core.reasoning.orchestrator import ReasoningOrchestrator as ReasoningOrchestratorType

logger = logging.getLogger(__name__)


def _serialize_columns(columns: list[Any] | None) -> list[dict[str, Any]] | None:
    if columns is None:
        return None
    serialized: list[dict[str, Any]] = []
    for col in columns:
        if hasattr(col, "model_dump"):
            serialized.append(col.model_dump())
        else:
            serialized.append(asdict(col))
    return serialized


@dataclass
class TurnContext:
    session_id: str
    turn_id: str
    schema: Any | None
    messages: list[ChatMessage]
    user_message: str
    metadata: dict[str, Any]
    enhancement_enabled: bool
    enhancement_requested: bool = False
    database_id: str = DEFAULT_DATABASE_ID
    last_explainability: ChatMessageExplainability | None = None


@dataclass
class InScopeTurnData:
    exec_result: ExecuteQueryResult | None
    chart: Any | None
    meta: dict[str, Any]
    system: str
    reasoning: ReasoningMetadata | None = None
    clarification_only: bool = False


@dataclass
class ChatResult:
    session_id: str
    message: str
    sources: list[str] = field(default_factory=list)
    sql: str | None = None
    results: list[dict[str, Any]] | None = None
    columns: list[Any] | None = None
    chart: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _apply_trust_to_chat_result(result: ChatResult) -> ChatResult:
    """Strip trust fields from chat JSON when explainability is disabled."""
    if is_trust_explainability_enabled():
        return result
    gated = apply_trust_gating_to_chat_response(
        {
            "session_id": result.session_id,
            "message": result.message,
            "sources": result.sources,
            "sql": result.sql,
            "results": result.results,
            "columns": result.columns,
            "metadata": result.metadata,
        }
    )
    return ChatResult(
        session_id=str(gated["session_id"]),
        message=str(gated["message"]),
        sources=list(gated.get("sources") or []),
        sql=gated.get("sql"),
        results=gated.get("results"),
        columns=gated.get("columns"),
        chart=result.chart,
        metadata=dict(gated.get("metadata") or {}),
    )


class ChatService:
    def __init__(
        self,
        *,
        planner: QueryPlanner,
        registry: DatabaseRegistry,
        sessions: BaseSessionStore,
        orchestrator: EnhancementOrchestrator | None,
        catalog: Any | None,
        semantic_registry: Any | None,
        reasoning_orchestrator: ReasoningOrchestratorType | None = None,
    ) -> None:
        self._planner = planner
        self._registry = registry
        self._sessions = sessions
        self._orchestrator = orchestrator
        self._catalog = catalog
        self._semantic = semantic_registry
        self._reasoning = reasoning_orchestrator or build_default_orchestrator()
        self._client = get_async_client()
        self._model = get_model()
        self._api_base = get_api_base()
        self._api_key = get_api_key()
        self._retriever = ContextRetriever()

    async def handle_json(
        self,
        *,
        message: str,
        session_id: str | None,
        messages_override: list[ChatMessage] | None,
        include_charts: bool,
        enhancement_enabled: bool | None,
        database_id: str = DEFAULT_DATABASE_ID,
    ) -> ChatResult:
        ctx = await self._prepare_turn(
            message,
            session_id,
            messages_override,
            enhancement_enabled,
            database_id,
        )
        result = await self._run_turn(ctx, include_charts=include_charts)
        should_pin = (
            not result.metadata.get("refusal")
            and not result.metadata.get("clarification_only")
            and not result.metadata.get("sql_error")
        )
        await self._persist_turn_messages(
            ctx,
            user_message=message,
            assistant_message=result.message,
            pin_database=should_pin,
        )
        return result

    async def prepare_stream_turn(
        self,
        *,
        message: str,
        session_id: str | None,
        messages_override: list[ChatMessage] | None,
        enhancement_enabled: bool | None,
        database_id: str = DEFAULT_DATABASE_ID,
    ) -> TurnContext:
        """Validate session/database before opening an SSE stream."""
        return await self._prepare_turn(
            message,
            session_id,
            messages_override,
            enhancement_enabled,
            database_id,
        )

    async def stream_turn(
        self,
        ctx: TurnContext,
        *,
        message: str,
        include_charts: bool,
    ) -> AsyncIterator[str]:
        try:
            async for chunk in self._stream_turn_impl(
                ctx,
                message=message,
                include_charts=include_charts,
            ):
                yield chunk
        except Exception as exc:
            mapped = llm_http_error(exc)
            if mapped is None:
                logger.exception("Chat stream failed")
            else:
                logger.warning("Chat stream failed: %s", exc)
            yield llm_stream_error_sse(exc, mapped=mapped)
            yield "data: [DONE]\n\n"

    async def _stream_turn_impl(
        self,
        ctx: TurnContext,
        *,
        message: str,
        include_charts: bool,
    ) -> AsyncIterator[str]:
        scope = await self._scope_gate(ctx)
        if not scope.in_scope:
            async for chunk in self._refusal_stream(ctx, scope):
                yield chunk
            return

        turn = await self._in_scope_turn_pipeline(ctx, include_charts=include_charts)
        ctx.last_explainability = self._explainability_snapshot_from_turn(ctx, turn)
        yield self._format_meta_event(ctx, turn)

        if turn.clarification_only and turn.reasoning is not None:
            clarification = clarification_message(turn.reasoning)
            yield format_openai_sse_delta(clarification)
            await self._persist_turn_messages(
                ctx,
                user_message=message,
                assistant_message=clarification,
                pin_database=False,
            )
            yield "data: [DONE]\n\n"
            return

        llm_messages = self._build_answer_messages(ctx, turn.exec_result, turn.system)

        full_text: list[str] = []
        completed = False
        try:
            response = await litellm.acompletion(
                model=self._model,
                messages=llm_messages,
                stream=True,
                api_base=self._api_base,
                api_key=self._api_key,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full_text.append(delta)
                    yield format_openai_sse_delta(delta)

            completed = True
        finally:
            if completed:
                streamed = "".join(full_text)
                assistant, final_reasoning = await self._produce_answer(
                    ctx,
                    turn,
                    streamed_message=streamed,
                )
                turn.reasoning = final_reasoning
                ctx.last_explainability = self._explainability_snapshot_from_turn(ctx, turn)

                suffix = reasoning_suffix_delta(streamed, final_reasoning)
                if suffix:
                    yield format_openai_sse_delta(suffix)

                yield self._format_meta_event(ctx, turn)
                await self._persist_turn_messages(
                    ctx,
                    user_message=message,
                    assistant_message=assistant,
                    pin_database=not turn.meta.get("sql_error"),
                )

        yield "data: [DONE]\n\n"

    async def handle_stream(
        self,
        *,
        message: str,
        session_id: str | None,
        messages_override: list[ChatMessage] | None,
        include_charts: bool,
        enhancement_enabled: bool | None,
        database_id: str = DEFAULT_DATABASE_ID,
    ) -> AsyncIterator[str]:
        ctx = await self.prepare_stream_turn(
            message=message,
            session_id=session_id,
            messages_override=messages_override,
            enhancement_enabled=enhancement_enabled,
            database_id=database_id,
        )
        async for chunk in self.stream_turn(ctx, message=message, include_charts=include_charts):
            yield chunk

    async def _prepare_turn(
        self,
        message: str,
        session_id: str | None,
        messages_override: list[ChatMessage] | None,
        enhancement_enabled: bool | None,
        database_id: str,
    ) -> TurnContext:
        settings = get_settings()
        sid, state = await self._sessions.get_or_create(session_id)
        if state.database_id is not None and state.database_id != database_id:
            raise SessionDatabaseMismatchError(
                session_id=sid,
                pinned_database_id=state.database_id,
                requested_database_id=database_id,
            )
        history = list(messages_override or state.messages)
        if messages_override:
            total = sum(len(m.content) for m in history)
            if total > settings.max_chat_history_chars:
                raise ValueError(
                    f"Chat history exceeds {settings.max_chat_history_chars} characters"
                )
        messages = history + [ChatMessage(role="user", content=message)]

        enh_on = (
            enhancement_enabled
            if enhancement_enabled is not None
            else settings.chat_enhancement_enabled
        )

        return TurnContext(
            session_id=sid,
            turn_id=str(uuid.uuid4()),
            schema=None,
            messages=messages,
            user_message=message,
            metadata={"database_id": database_id},
            enhancement_enabled=enh_on and self._orchestrator is not None,
            enhancement_requested=enh_on,
            database_id=database_id,
        )

    def _enhancement_metadata_kwargs(self, ctx: TurnContext) -> dict[str, bool]:
        return {
            "vector_rag_available": (
                self._orchestrator.vector_rag_available() if self._orchestrator else False
            ),
            "enhancement_requested": ctx.enhancement_requested,
            "orchestrator_available": self._orchestrator is not None,
        }

    def _explainability_snapshot_from_turn(
        self,
        ctx: TurnContext,
        turn: InScopeTurnData,
    ) -> ChatMessageExplainability:
        used_sql = turn.exec_result is not None
        metadata = build_chat_metadata(
            database_id=ctx.database_id,
            exec_result=turn.exec_result,
            used_sql=used_sql,
            enhancement_enabled=ctx.enhancement_enabled,
            applied=list(ctx.metadata.get("applied", [])),
            scope=ctx.metadata.get("scope"),
            sql_error=bool(turn.meta.get("sql_error")),
            reasoning=turn.reasoning,
            catalog_matches=self._catalog_matches_for_context(ctx),
            **self._enhancement_metadata_kwargs(ctx),
        )
        enforce_nested_chat_metadata(
            metadata,
            sql=turn.exec_result.sql if turn.exec_result else None,
        )
        preview = turn.exec_result.rows[:50] if turn.exec_result else []
        chart_dict = turn.chart.model_dump() if turn.chart is not None else None
        return ChatMessageExplainability(
            sql=turn.exec_result.sql if turn.exec_result else None,
            sources=list(ctx.metadata.get("sources", [])),
            metadata=metadata,
            chart=chart_dict,
            results=preview,
        )

    def _explainability_snapshot_from_metadata(
        self,
        metadata: dict[str, Any],
    ) -> ChatMessageExplainability:
        return ChatMessageExplainability(metadata=dict(metadata))

    async def _persist_turn_messages(
        self,
        ctx: TurnContext,
        *,
        user_message: str,
        assistant_message: str,
        pin_database: bool,
    ) -> None:
        """Append turn messages to the session store; pin database after in-scope success."""
        await self._sessions.append(ctx.session_id, ChatMessage(role="user", content=user_message))
        if assistant_message.strip():
            await self._sessions.append(
                ctx.session_id,
                ChatMessage(
                    role="assistant",
                    content=assistant_message,
                    explainability=ctx.last_explainability,
                ),
            )
        if pin_database:
            await self._complete_turn(ctx)

    async def _complete_turn(self, ctx: TurnContext) -> None:
        """Pin database_id after a successful turn."""
        await self._sessions.set_database_id(ctx.session_id, ctx.database_id)

    async def _ensure_schema(self, ctx: TurnContext) -> None:
        if ctx.schema is not None:
            return
        bundle = self._registry.get(ctx.database_id)
        ctx.schema = await bundle.introspector.introspect()

    async def _ensure_schema_for_enhancement(self, ctx: TurnContext) -> None:
        if ctx.enhancement_enabled and self._orchestrator:
            await self._ensure_schema(ctx)

    def _planner_resources(self, database_id: str) -> tuple[Any | None, Any | None]:
        return planner_resources_for_database(
            database_id,
            catalog=self._catalog,
            semantic_registry=self._semantic,
        )

    def _enhancement_context(
        self,
        ctx: TurnContext,
        *,
        stage: str,
        base_system_prompt: str,
        user_message: str,
        include_charts: bool = False,
    ) -> EnhancementContext:
        in_scope = bool(ctx.metadata.get("scope", {}).get("in_scope", True))
        return EnhancementContext(
            session_id=ctx.session_id,
            turn_id=ctx.turn_id,
            stage=stage,
            user_message=user_message,
            messages=ctx.messages,
            base_system_prompt=base_system_prompt,
            database_schema=ctx.schema,
            include_charts=include_charts,
            in_scope=in_scope,
            metadata=dict(ctx.metadata),
        )

    def _database_capabilities(self, database_id: str) -> DatabaseCapabilities:
        bundle = self._registry.get(database_id)
        return DatabaseCapabilities.from_bundle(
            database_id=database_id,
            dialect=bundle.dialect,
        )

    def _schema_table_count(self, ctx: TurnContext) -> int | None:
        if ctx.schema is not None and hasattr(ctx.schema, "tables"):
            return len(ctx.schema.tables)
        return None

    def _schema_table_names(self, ctx: TurnContext) -> tuple[str, ...]:
        if ctx.schema is not None and hasattr(ctx.schema, "tables"):
            return tuple(t.name for t in ctx.schema.tables if hasattr(t, "name"))
        return ()

    def _scope_table_names(self, ctx: TurnContext) -> tuple[str, ...]:
        return merge_table_name_hints(
            self._schema_table_names(ctx),
            catalog_table_names(self._catalog),
        )

    def _resolved_user_message(self, ctx: TurnContext) -> str:
        return effective_user_message(
            user_message=ctx.user_message,
            messages=ctx.messages,
        )

    def _reasoning_context(
        self,
        ctx: TurnContext,
        *,
        exec_result: ExecuteQueryResult | None,
        phase: ReasoningPhase,
    ) -> ReasoningContext:
        return ReasoningContext(
            route="chat",
            user_message=self._resolved_user_message(ctx),
            database_capabilities=self._database_capabilities(ctx.database_id),
            phase=phase,
            messages=tuple(ctx.messages) if ctx.messages else None,
            exec_result=exec_result,
            schema_table_count=self._schema_table_count(ctx),
            schema_table_names=self._scope_table_names(ctx),
        )

    def _reasoning_from_decision(self, decision: ChatDecision) -> ReasoningMetadata:
        """Merge LLM decision fields; heuristics in pre-phase take precedence via merge order."""
        return ReasoningMetadata(
            inferred_context=list(decision.inferred_context),
            clarifying_questions=list(decision.clarifying_questions),
            clarification_required=decision.clarification_required,
            layers_applied=["chat_decision_llm"],
        )

    def _reasoning_from_answer(
        self,
        answer: ChatAnswer | ChatAnswerEnrichment,
    ) -> ReasoningMetadata:
        return ReasoningMetadata(
            analysis_followups=list(answer.analysis_followups),
            research_notes=list(answer.research_notes),
            layers_applied=["chat_answer_llm"],
        )

    async def _produce_answer(
        self,
        ctx: TurnContext,
        turn: InScopeTurnData,
        *,
        streamed_message: str | None = None,
    ) -> tuple[str, ReasoningMetadata]:
        """Produce final assistant text and merged reasoning (JSON + stream parity)."""
        llm_messages = self._build_answer_messages(ctx, turn.exec_result, turn.system)

        if streamed_message is not None:
            enrichment_messages = [
                {"role": "system", "content": CHAT_ANSWER_ENRICHMENT_SYSTEM},
                *llm_messages[1:],
                {"role": "assistant", "content": streamed_message},
            ]
            enrichment = await self._client.chat.completions.create(
                model=self._model,
                messages=enrichment_messages,
                response_model=ChatAnswerEnrichment,
                api_base=self._api_base,
                api_key=self._api_key,
                max_retries=get_settings().llm_max_retries,
            )
            reasoning = merge_answer_reasoning(
                turn.reasoning,
                self._reasoning_from_answer(enrichment),  # type: ignore[arg-type]
            )
            message = append_reasoning_to_message(streamed_message, reasoning)
            return message, reasoning

        answer = await self._client.chat.completions.create(
            model=self._model,
            messages=llm_messages,
            response_model=ChatAnswer,
            api_base=self._api_base,
            api_key=self._api_key,
            max_retries=get_settings().llm_max_retries,
        )
        reasoning = merge_answer_reasoning(
            turn.reasoning,
            self._reasoning_from_answer(answer),  # type: ignore[arg-type]
        )
        message = append_reasoning_to_message(
            answer.message,  # type: ignore[union-attr]
            reasoning,
        )
        return message, reasoning

    async def _in_scope_turn_pipeline(
        self, ctx: TurnContext, *, include_charts: bool
    ) -> InScopeTurnData:
        await self._ensure_schema_for_enhancement(ctx)
        pre_ctx = self._reasoning_context(
            ctx,
            exec_result=None,
            phase=ReasoningPhase.PRE_EXECUTION,
        )
        pre_reasoning = normalize_reasoning_clarification(await self._reasoning.run_pre(pre_ctx))
        if should_return_clarification(pre_reasoning):
            return InScopeTurnData(
                exec_result=None,
                chart=None,
                meta={},
                system="",
                reasoning=pre_reasoning,
                clarification_only=True,
            )

        decision = await self._chat_decision(ctx)
        merged_pre = normalize_reasoning_clarification(
            merge_reasoning_metadata(
                pre_reasoning,
                self._reasoning_from_decision(decision),
            )
        )
        if should_return_clarification(merged_pre):
            return InScopeTurnData(
                exec_result=None,
                chart=None,
                meta={},
                system="",
                reasoning=merged_pre,
                clarification_only=True,
            )

        if decision.needs_data:
            exec_result, chart, meta = await self._execute_data_path(
                ctx, include_charts and decision.needs_data
            )
        else:
            exec_result, chart, meta = None, None, {}
            await self._ensure_schema_for_enhancement(ctx)

        post_ctx = self._reasoning_context(
            ctx,
            exec_result=exec_result,
            phase=ReasoningPhase.POST_EXECUTION,
        )
        post_reasoning = await self._reasoning.run_post(post_ctx)
        reasoning = merge_reasoning_metadata(merged_pre, post_reasoning)

        system = await self._answer_system(ctx, meta)
        return InScopeTurnData(
            exec_result=exec_result,
            chart=chart,
            meta=meta,
            system=system,
            reasoning=reasoning,
        )

    def _format_meta_event(self, ctx: TurnContext, turn: InScopeTurnData) -> str:
        preview_rows: list[dict[str, object]] | None = None
        preview_columns = None
        if turn.exec_result:
            preview_rows = turn.exec_result.rows[:50]
            preview_columns = turn.exec_result.columns

        used_sql = turn.exec_result is not None
        meta_event = build_stream_meta_event(
            session_id=ctx.session_id,
            database_id=ctx.database_id,
            exec_result=turn.exec_result,
            used_sql=used_sql,
            enhancement_enabled=ctx.enhancement_enabled,
            applied=list(ctx.metadata.get("applied", [])),
            sources=list(ctx.metadata.get("sources", [])),
            sql=turn.exec_result.sql if turn.exec_result else None,
            results=preview_rows,
            columns=_serialize_columns(preview_columns),
            chart=turn.chart.model_dump() if turn.chart is not None else None,
            scope=ctx.metadata.get("scope"),
            sql_error=bool(turn.meta.get("sql_error")),
            reasoning=turn.reasoning,
            catalog_matches=self._catalog_matches_for_context(ctx),
            **self._enhancement_metadata_kwargs(ctx),
        )
        meta_event = apply_trust_gating_to_stream_meta(meta_event)
        enforce_stream_meta_validation(meta_event)
        return f"event: seal.meta\ndata: {safe_json_dumps(meta_event)}\n\n"

    def _catalog_matches_for_context(self, ctx: TurnContext) -> list[dict[str, Any]]:
        sources = ctx.metadata.get("sources")
        if not ctx.schema or not isinstance(sources, list) or not sources:
            return []
        return build_catalog_matches(sources, ctx.schema, self._catalog)

    async def _run_turn(self, ctx: TurnContext, *, include_charts: bool) -> ChatResult:
        scope = await self._scope_gate(ctx)
        if not scope.in_scope:
            return await self._refusal_turn(ctx, scope)

        turn = await self._in_scope_turn_pipeline(ctx, include_charts=include_charts)
        if turn.clarification_only and turn.reasoning is not None:
            return self._clarification_result(ctx, turn)

        message, reasoning = await self._produce_answer(ctx, turn)

        preview = None
        columns: list[dict[str, Any]] | None = None
        if turn.exec_result:
            preview = turn.exec_result.rows[:50]
            columns = _serialize_columns(turn.exec_result.columns)

        # True only when SQL executed successfully; sql_error turns keep used_sql False.
        used_sql = turn.exec_result is not None
        metadata = build_chat_metadata(
            database_id=ctx.database_id,
            exec_result=turn.exec_result,
            used_sql=used_sql,
            enhancement_enabled=ctx.enhancement_enabled,
            applied=list(ctx.metadata.get("applied", [])),
            scope=ctx.metadata.get("scope"),
            sql_error=bool(turn.meta.get("sql_error")),
            reasoning=reasoning,
            catalog_matches=self._catalog_matches_for_context(ctx),
            **self._enhancement_metadata_kwargs(ctx),
        )
        enforce_nested_chat_metadata(
            metadata,
            sql=turn.exec_result.sql if turn.exec_result else None,
        )
        turn.reasoning = reasoning
        ctx.last_explainability = self._explainability_snapshot_from_metadata(metadata)

        return _apply_trust_to_chat_result(
            ChatResult(
                session_id=ctx.session_id,
                message=message,
                sources=list(ctx.metadata.get("sources", [])),
                sql=turn.exec_result.sql if turn.exec_result else None,
                results=preview,
                columns=columns,
                chart=turn.chart,
                metadata=metadata,
            )
        )

    def _clarification_result(self, ctx: TurnContext, turn: InScopeTurnData) -> ChatResult:
        reasoning = normalize_reasoning_clarification(turn.reasoning or ReasoningMetadata())
        message = clarification_message(reasoning)
        metadata = build_chat_metadata(
            database_id=ctx.database_id,
            exec_result=None,
            used_sql=False,
            enhancement_enabled=ctx.enhancement_enabled,
            applied=list(ctx.metadata.get("applied", [])),
            scope=ctx.metadata.get("scope"),
            reasoning=reasoning,
            catalog_matches=self._catalog_matches_for_context(ctx),
            **self._enhancement_metadata_kwargs(ctx),
        )
        metadata["clarification_only"] = True
        enforce_nested_chat_metadata(metadata, sql=None)
        ctx.last_explainability = self._explainability_snapshot_from_metadata(metadata)
        return _apply_trust_to_chat_result(
            ChatResult(
                session_id=ctx.session_id,
                message=message,
                metadata=metadata,
            )
        )

    async def _scope_gate(self, ctx: TurnContext):
        scope = await classify_scope(
            ctx.user_message,
            channel="chat",
            prior_messages=tuple(ctx.messages) if ctx.messages else None,
            schema_table_names=self._scope_table_names(ctx),
        )
        ctx.metadata["scope"] = ScopeMetadata.from_result(scope).model_dump(exclude_none=True)
        return scope

    async def _refusal_turn(self, ctx: TurnContext, scope: ScopeResult) -> ChatResult:
        heuristic = suggest_queries(scope)
        metadata = build_chat_metadata(
            database_id=ctx.database_id,
            exec_result=None,
            used_sql=False,
            enhancement_enabled=False,
            applied=[],
            scope=ctx.metadata.get("scope"),
            refusal=True,
            suggested_queries=heuristic,
            **self._enhancement_metadata_kwargs(ctx),
        )
        enforce_nested_chat_metadata(metadata, sql=None)
        ctx.last_explainability = self._explainability_snapshot_from_metadata(metadata)
        if scope.source == "limits":
            return _apply_trust_to_chat_result(
                ChatResult(
                    session_id=ctx.session_id,
                    message=LIMIT_REFUSAL_MESSAGE,
                    metadata=metadata,
                )
            )

        answer = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": REFUSAL_SYSTEM},
                {"role": "user", "content": ctx.user_message},
            ],
            response_model=ChatAnswer,
            api_base=self._api_base,
            api_key=self._api_key,
            max_retries=get_settings().llm_max_retries,
        )
        llm_suggestions = getattr(answer, "suggested_queries", None)
        final_suggestions = merge_suggestions(heuristic, llm_suggestions)
        metadata["suggested_queries"] = final_suggestions
        enforce_nested_chat_metadata(metadata, sql=None)
        ctx.last_explainability = self._explainability_snapshot_from_metadata(metadata)
        return _apply_trust_to_chat_result(
            ChatResult(
                session_id=ctx.session_id,
                message=answer.message,  # type: ignore[union-attr]
                metadata=metadata,
            )
        )

    async def _refusal_stream(self, ctx: TurnContext, scope) -> AsyncIterator[str]:
        result = await self._refusal_turn(ctx, scope)
        suggested = result.metadata.get("suggested_queries")
        meta_event = build_stream_meta_event(
            session_id=ctx.session_id,
            database_id=ctx.database_id,
            exec_result=None,
            used_sql=False,
            enhancement_enabled=False,
            applied=[],
            sources=[],
            sql=None,
            results=None,
            columns=None,
            chart=None,
            scope=ctx.metadata.get("scope"),
            refusal=True,
            suggested_queries=suggested if isinstance(suggested, list) else None,
            **self._enhancement_metadata_kwargs(ctx),
        )
        meta_event = apply_trust_gating_to_stream_meta(meta_event)
        enforce_stream_meta_validation(meta_event)
        yield f"event: seal.meta\ndata: {safe_json_dumps(meta_event)}\n\n"
        payload = {
            "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": {"content": result.message}, "finish_reason": None}],
        }
        yield f"data: {safe_json_dumps(payload)}\n\n"
        await self._persist_turn_messages(
            ctx,
            user_message=ctx.user_message,
            assistant_message=result.message,
            pin_database=False,
        )
        yield "data: [DONE]\n\n"

    async def _chat_decision(self, ctx: TurnContext) -> ChatDecision:
        system = CHAT_DECISION_SYSTEM
        if ctx.enhancement_enabled and self._orchestrator:
            ect = self._enhancement_context(
                ctx,
                stage="decision",
                base_system_prompt=system,
                user_message=self._resolved_user_message(ctx),
            )
            system = await self._orchestrator.enhance_system_prompt(ect)
            ctx.metadata.update(ect.metadata)

        decision_history_turns = 3
        recent: list[ChatMessage] = []
        user_turns = 0
        for m in reversed(ctx.messages):
            recent.append(m)
            if m.role == "user":
                user_turns += 1
                if user_turns >= decision_history_turns:
                    break
        recent.reverse()

        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        for m in recent:
            content = m.content
            if m.role == "assistant":
                content = content_for_llm_history(content)
            messages.append({"role": m.role, "content": content})
        if not any(m["role"] == "user" for m in messages[1:]):
            last_content = ctx.messages[-1].content if ctx.messages else ""
            messages.append({"role": "user", "content": last_content})

        return await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            response_model=ChatDecision,
            api_base=self._api_base,
            api_key=self._api_key,
            max_retries=get_settings().llm_max_retries,
        )  # type: ignore[return-value]

    async def _execute_data_path(
        self, ctx: TurnContext, include_charts: bool
    ) -> tuple[ExecuteQueryResult | None, Any | None, dict[str, Any]]:
        await self._ensure_schema(ctx)

        question = self._resolved_user_message(ctx)
        semantic_registry, data_catalog = self._planner_resources(ctx.database_id)
        table_names = self._retriever.select_tables(
            question,
            ctx.schema,
            data_catalog,
            full_schema=include_charts,
        )
        ctx.metadata["sources"] = table_names

        try:
            bundle = self._registry.get(ctx.database_id)
            exec_result = await execute_natural_language_query(
                question=question,
                schema=ctx.schema,
                planner=self._planner,
                executor=bundle.executor,
                semantic_registry=semantic_registry,
                data_catalog=data_catalog,
                table_names=table_names if not include_charts else None,
            )
        except UnknownDatabaseError:
            raise
        except Exception as e:
            logger.error("Chat SQL path failed: %s", e)
            return None, None, {"sql_error": True}

        chart = None
        if include_charts:
            from seal_sql.result import QueryResult

            qr = QueryResult(
                columns=exec_result.columns,
                rows=exec_result.rows,
                row_count=exec_result.row_count,
                execution_time_ms=exec_result.execution_time_ms,
                truncated=exec_result.truncated,
                sql=exec_result.sql,
            )
            chart = ChartEngine.generate(exec_result.plan, qr)

        return exec_result, chart, {"used_sql": True}

    async def _answer_system(self, ctx: TurnContext, meta: dict[str, Any]) -> str:
        base = CHAT_ANSWER_SYSTEM
        if not ctx.enhancement_enabled or not self._orchestrator:
            return base
        ect = self._enhancement_context(
            ctx,
            stage="answer",
            base_system_prompt=base,
            user_message=self._resolved_user_message(ctx),
        )
        system = await self._orchestrator.enhance_system_prompt(ect)
        ctx.metadata.update(ect.metadata)
        return system

    def _build_answer_messages(
        self,
        ctx: TurnContext,
        exec_result: ExecuteQueryResult | None,
        system: str,
    ) -> list[dict[str, str]]:
        settings = get_settings()
        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        for m in ctx.messages[-settings.chat_recent_messages :]:
            content = m.content
            if m.role == "assistant":
                content = content_for_llm_history(content)
            messages.append({"role": m.role, "content": content})
        if not any(m["role"] == "user" for m in messages[1:]):
            last_content = ctx.messages[-1].content if ctx.messages else ""
            messages.append({"role": "user", "content": last_content})

        if exec_result:
            preview = safe_json_dumps(exec_result.rows[: settings.chat_answer_preview_rows])
            messages.append(
                {
                    "role": "user",
                    "content": f"Query results (use these facts only):\n{preview}",
                }
            )
        return messages
