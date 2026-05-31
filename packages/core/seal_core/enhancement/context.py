"""Enhancement context passed to PromptEnhancer hooks."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from seal_core.chat.models import ChatMessage  # noqa: TC001
from seal_core.schema.models import DatabaseSchema  # noqa: TC001


class EnhancementContext(BaseModel):
    session_id: str
    turn_id: str
    stage: Literal["decision", "planner", "answer"]
    user_message: str
    messages: list[ChatMessage] = Field(default_factory=list)
    base_system_prompt: str = ""
    database_schema: DatabaseSchema | None = Field(default=None, alias="schema")
    include_charts: bool = False
    in_scope: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}
