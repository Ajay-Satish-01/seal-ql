"""Chat orchestration service."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import litellm
from seal_charts.engine import ChartEngine

from seal_core.chat.models import ChatAnswer, ChatDecision, ChatMessage
from seal_core.chat.prompts import CHAT_ANSWER_SYSTEM, CHAT_DECISION_SYSTEM
from seal_core.chat.retriever import ContextRetriever
from seal_core.enhancement.context import EnhancementContext
from seal_core.guardrails.prompts import LIMIT_REFUSAL_MESSAGE, REFUSAL_SYSTEM
from seal_core.guardrails.scope import classify_scope
from seal_core.llm.client import get_api_base, get_api_key, get_async_client, get_model
from seal_core.pipeline.execute import ExecuteQueryResult, execute_natural_language_query
from seal_core.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from seal_sql.executor import QueryExecutor

    from seal_core.chat.sessions import SessionStore
    from seal_core.enhancement.orchestrator import EnhancementOrchestrator
    from seal_core.planner.planner import QueryPlanner

logger = logging.getLogger(__name__)


@dataclass
class TurnContext:
    session_id: str
    turn_id: str
    schema: Any
    messages: list[ChatMessage]
    user_message: str
    metadata: dict[str, Any]
    enhancement_enabled: bool


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


class ChatService:
    def __init__(
        self,
        *,
        planner: QueryPlanner,
        executor: QueryExecutor,
        sessions: SessionStore,
        orchestrator: EnhancementOrchestrator | None,
        catalog: Any | None,
        semantic_registry: Any | None,
    ) -> None:
        self._planner = planner
        self._executor = executor
        self._sessions = sessions
        self._orchestrator = orchestrator
        self._catalog = catalog
        self._semantic = semantic_registry
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
        schema: Any,
    ) -> ChatResult:
        ctx = self._prepare_turn(
            message, session_id, messages_override, enhancement_enabled, schema
        )
        result = await self._run_turn(ctx, include_charts=include_charts)
        self._sessions.append(ctx.session_id, ChatMessage(role="user", content=message))
        self._sessions.append(ctx.session_id, ChatMessage(role="assistant", content=result.message))
        return result

    async def handle_stream(
        self,
        *,
        message: str,
        session_id: str | None,
        messages_override: list[ChatMessage] | None,
        include_charts: bool,
        enhancement_enabled: bool | None,
        schema: Any,
    ) -> AsyncIterator[str]:
        ctx = self._prepare_turn(
            message, session_id, messages_override, enhancement_enabled, schema
        )
        scope = await self._scope_gate(ctx)
        if not scope.in_scope:
            async for chunk in self._refusal_stream(ctx, scope):
                yield chunk
            return

        decision = await self._chat_decision(ctx)
        exec_result: ExecuteQueryResult | None = None
        chart = None
        if decision.needs_data:
            exec_result, chart, data_meta = await self._execute_data_path(
                ctx, include_charts and decision.needs_data
            )
        else:
            exec_result, chart, data_meta = None, None, {}

        # Run the same enhancement path as _run_turn so streamed answers are
        # schema/RAG/multi-turn aware instead of falling back to the base prompt.
        system = await self._answer_system(ctx, data_meta)

        preview_rows: list[dict[str, object]] | None = None
        preview_columns = None
        if exec_result:
            preview_rows = exec_result.rows[:50]
            preview_columns = exec_result.columns

        meta_event = {
            "session_id": ctx.session_id,
            "sources": ctx.metadata.get("sources", []),
            "sql": exec_result.sql if exec_result else None,
            "results": preview_rows,
            "columns": (
                [c.model_dump() for c in preview_columns] if preview_columns is not None else None
            ),
            "chart": chart.model_dump() if chart is not None else None,
            "enhancement": {
                "enabled": ctx.enhancement_enabled,
                "applied": list(ctx.metadata.get("applied", [])),
            },
            "scope": ctx.metadata.get("scope"),
        }
        yield f"event: seal.meta\ndata: {json.dumps(meta_event)}\n\n"

        llm_messages = self._build_answer_messages(ctx, exec_result, system)

        # Plain-text token streaming (not the Instructor/response_model path used by
        # handle_json): structured fields are already sent in the single seal.meta
        # event above, and the SSE contract streams the answer body as raw text deltas.
        full_text: list[str] = []
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
                    payload = {
                        "object": "chat.completion.chunk",
                        "choices": [
                            {"index": 0, "delta": {"content": delta}, "finish_reason": None}
                        ],
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

            yield "data: [DONE]\n\n"
        finally:
            # Persist the turn even if the stream errors mid-flight, so partial
            # assistant output is not silently dropped from session history.
            assistant = "".join(full_text)
            self._sessions.append(ctx.session_id, ChatMessage(role="user", content=message))
            if assistant.strip():
                self._sessions.append(
                    ctx.session_id,
                    ChatMessage(role="assistant", content=assistant),
                )

    def _prepare_turn(
        self,
        message: str,
        session_id: str | None,
        messages_override: list[ChatMessage] | None,
        enhancement_enabled: bool | None,
        schema: Any,
    ) -> TurnContext:
        settings = get_settings()
        sid, state = self._sessions.get_or_create(session_id)
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
            schema=schema,
            messages=messages,
            user_message=message,
            metadata={},
            enhancement_enabled=enh_on and self._orchestrator is not None,
        )

    async def _run_turn(self, ctx: TurnContext, *, include_charts: bool) -> ChatResult:
        scope = await self._scope_gate(ctx)
        if not scope.in_scope:
            return await self._refusal_turn(ctx, scope)

        decision = await self._chat_decision(ctx)
        exec_result: ExecuteQueryResult | None = None
        chart = None

        if decision.needs_data:
            exec_result, chart, meta = await self._execute_data_path(
                ctx, include_charts and decision.needs_data
            )
        else:
            meta = {}

        system = await self._answer_system(ctx, meta)
        ctx.metadata["answer_system"] = system
        llm_messages = self._build_answer_messages(ctx, exec_result, system)

        answer = await self._client.chat.completions.create(
            model=self._model,
            messages=llm_messages,
            response_model=ChatAnswer,
            api_base=self._api_base,
            api_key=self._api_key,
            max_retries=get_settings().llm_max_retries,
        )

        preview = None
        columns = None
        if exec_result:
            preview = exec_result.rows[:50]
            columns = exec_result.columns

        return ChatResult(
            session_id=ctx.session_id,
            message=answer.message,  # type: ignore[union-attr]
            sources=list(ctx.metadata.get("sources", [])),
            sql=exec_result.sql if exec_result else None,
            results=preview,
            columns=columns,
            chart=chart,
            metadata={
                "used_sql": exec_result is not None,
                "repair_attempts": exec_result.repair_attempts if exec_result else 0,
                "enhancement": meta,
                "scope": ctx.metadata.get("scope"),
            },
        )

    async def _scope_gate(self, ctx: TurnContext):
        scope = await classify_scope(ctx.user_message, channel="chat")
        ctx.metadata["scope"] = {
            "in_scope": scope.in_scope,
            "reason": scope.reason,
            "source": scope.source,
        }
        return scope

    async def _refusal_turn(self, ctx: TurnContext, scope) -> ChatResult:
        # Size-limit violations are refused with a static message: forwarding the
        # oversized user message to the LLM would defeat the limit's purpose.
        if getattr(scope, "source", None) == "limits":
            return ChatResult(
                session_id=ctx.session_id,
                message=LIMIT_REFUSAL_MESSAGE,
                metadata={"scope": ctx.metadata.get("scope"), "refusal": True},
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
        return ChatResult(
            session_id=ctx.session_id,
            message=answer.message,  # type: ignore[union-attr]
            metadata={"scope": ctx.metadata.get("scope"), "refusal": True},
        )

    async def _refusal_stream(self, ctx: TurnContext, scope) -> AsyncIterator[str]:
        result = await self._refusal_turn(ctx, scope)
        meta_event = {
            "session_id": ctx.session_id,
            "sources": [],
            "sql": None,
            "chart": None,
            "enhancement": {"enabled": False, "applied": []},
            "scope": ctx.metadata.get("scope"),
        }
        yield f"event: seal.meta\ndata: {json.dumps(meta_event)}\n\n"
        payload = {
            "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": {"content": result.message}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(payload)}\n\n"
        yield "data: [DONE]\n\n"
        self._sessions.append(ctx.session_id, ChatMessage(role="user", content=ctx.user_message))
        self._sessions.append(
            ctx.session_id,
            ChatMessage(role="assistant", content=result.message),
        )

    async def _chat_decision(self, ctx: TurnContext) -> ChatDecision:
        system = CHAT_DECISION_SYSTEM
        if ctx.enhancement_enabled and self._orchestrator:
            in_scope = bool(ctx.metadata.get("scope", {}).get("in_scope", True))
            ect = EnhancementContext(
                session_id=ctx.session_id,
                turn_id=ctx.turn_id,
                stage="decision",
                user_message=ctx.user_message,
                messages=ctx.messages,
                base_system_prompt=system,
                database_schema=ctx.schema,
                include_charts=False,
                in_scope=in_scope,
                metadata=dict(ctx.metadata),
            )
            system = await self._orchestrator.enhance_system_prompt(ect)
            ctx.metadata.update(ect.metadata)

        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        user_msg = ctx.messages[-1].content if ctx.messages else ""
        messages.append({"role": "user", "content": user_msg})

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
        question = ctx.user_message
        table_names = self._retriever.select_tables(
            question,
            ctx.schema,
            self._catalog,
            full_schema=include_charts,
        )
        ctx.metadata["sources"] = table_names

        try:
            exec_result = await execute_natural_language_query(
                question=question,
                schema=ctx.schema,
                planner=self._planner,
                executor=self._executor,
                semantic_registry=self._semantic,
                data_catalog=self._catalog,
                table_names=table_names if not include_charts else None,
            )
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
        in_scope = bool(ctx.metadata.get("scope", {}).get("in_scope", True))
        ect = EnhancementContext(
            session_id=ctx.session_id,
            turn_id=ctx.turn_id,
            stage="answer",
            user_message=ctx.messages[-1].content if ctx.messages else "",
            messages=ctx.messages,
            base_system_prompt=base,
            database_schema=ctx.schema,
            include_charts=False,
            in_scope=in_scope,
            metadata=dict(ctx.metadata),
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
            messages.append({"role": m.role, "content": m.content})
        if not any(m["role"] == "user" for m in messages[1:]):
            last_content = ctx.messages[-1].content if ctx.messages else ""
            messages.append({"role": "user", "content": last_content})

        if exec_result:
            preview = json.dumps(exec_result.rows[: settings.chat_answer_preview_rows], default=str)
            messages.append(
                {
                    "role": "user",
                    "content": f"Query results (use these facts only):\n{preview}",
                }
            )
        return messages
