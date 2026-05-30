import pytest
from seal_core.chat.models import ChatMessage
from seal_core.enhancement.context import EnhancementContext
from seal_core.enhancement.multiturn import MultiTurnEnhancer
from seal_core.enhancement.orchestrator import EnhancementOrchestrator
from seal_core.schema.models import DatabaseSchema


class _StubEnhancer:
    name = "stub"

    def enabled(self, ctx: EnhancementContext) -> bool:
        return True

    async def enhance_system_prompt(self, ctx: EnhancementContext) -> str:
        return ctx.base_system_prompt + "\nSTUB"

    async def enhance_user_messages(self, ctx: EnhancementContext) -> list[ChatMessage]:
        return ctx.messages


@pytest.mark.asyncio
async def test_orchestrator_chains_system_prompt() -> None:
    orch = EnhancementOrchestrator([_StubEnhancer(), MultiTurnEnhancer()])
    ctx = EnhancementContext(
        session_id="s1",
        turn_id="t1",
        stage="decision",
        user_message="hello",
        base_system_prompt="BASE",
        database_schema=DatabaseSchema(dialect="postgres", tables=[]),
    )
    out = await orch.enhance_system_prompt(ctx)
    assert "BASE" in out
    assert "STUB" in out


@pytest.mark.asyncio
async def test_orchestrator_fail_open() -> None:
    class _Fail:
        name = "fail"

        def enabled(self, ctx: EnhancementContext) -> bool:
            return True

        async def enhance_system_prompt(self, ctx: EnhancementContext) -> str:
            raise RuntimeError("boom")

        async def enhance_user_messages(self, ctx: EnhancementContext) -> list[ChatMessage]:
            return ctx.messages

    orch = EnhancementOrchestrator([_Fail()])
    ctx = EnhancementContext(
        session_id="s1",
        turn_id="t1",
        stage="decision",
        user_message="hi",
        base_system_prompt="SAFE",
    )
    assert await orch.enhance_system_prompt(ctx) == "SAFE"
