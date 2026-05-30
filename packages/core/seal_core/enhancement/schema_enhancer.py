"""Inject schema, catalog, and semantic context into system prompt."""

from __future__ import annotations

from typing import TYPE_CHECKING

from seal_core.chat.retriever import ContextRetriever
from seal_core.schema.models import DatabaseSchema

if TYPE_CHECKING:
    from seal_core.catalog.registry import DataCatalogRegistry
    from seal_core.chat.models import ChatMessage
    from seal_core.enhancement.context import EnhancementContext


class SchemaAwareEnhancer:
    name = "schema_aware"

    def __init__(
        self,
        catalog: DataCatalogRegistry | None = None,
        semantic_registry: object | None = None,
    ) -> None:
        self._catalog = catalog
        self._semantic = semantic_registry
        self._retriever = ContextRetriever()

    def enabled(self, ctx: EnhancementContext) -> bool:
        return ctx.database_schema is not None

    async def enhance_system_prompt(self, ctx: EnhancementContext) -> str:
        assert ctx.database_schema is not None
        history = " ".join(m.content for m in ctx.messages[-4:])
        table_names = self._retriever.select_tables(
            ctx.user_message,
            ctx.database_schema,
            self._catalog,
            history,
            full_schema=ctx.include_charts,
        )
        ctx.metadata["sources"] = table_names

        subset = DatabaseSchema(
            dialect=ctx.database_schema.dialect,
            tables=[t for t in ctx.database_schema.tables if t.name in table_names],
            relationships=[
                r
                for r in ctx.database_schema.relationships
                if r.from_table in table_names or r.to_table in table_names
            ],
            has_timescaledb=ctx.database_schema.has_timescaledb,
        )
        parts = [ctx.base_system_prompt, "\n## Schema\n", subset.to_prompt_context()]
        if self._catalog:
            parts.append(self._catalog.to_prompt_context(table_names))
        if self._semantic is not None:
            parts.append(self._semantic.get_context_string())
        return "\n".join(parts)

    async def enhance_user_messages(self, ctx: EnhancementContext) -> list[ChatMessage]:
        return ctx.messages
