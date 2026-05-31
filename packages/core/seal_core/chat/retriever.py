"""Keyword-based context retrieval for schema and catalog."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from seal_core.schema.models import DatabaseSchema, TableSchema
from seal_core.settings import get_settings

if TYPE_CHECKING:
    from seal_core.catalog.registry import DataCatalogRegistry


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text) if len(t) > 2}


class ContextRetriever:
    def select_tables(
        self,
        question: str,
        schema: DatabaseSchema,
        catalog: DataCatalogRegistry | None,
        history_text: str = "",
        *,
        max_tables: int | None = None,
        full_schema: bool = False,
    ) -> list[str]:
        if full_schema:
            return [t.name for t in schema.tables]

        limit = max_tables or get_settings().chat_max_context_tables
        tokens = _tokenize(question + " " + history_text)
        q_lower = question.lower()

        scores: dict[str, float] = {}
        for table in schema.tables:
            score = 0.0
            if table.name.lower() in q_lower:
                score += 10.0
            if catalog:
                entry = catalog.get_entry(table.name, table.schema_name)
                if entry:
                    desc = catalog.get_description(entry) or ""
                    for tok in tokens:
                        if tok in desc.lower():
                            score += 5.0
            for tok in tokens:
                if tok in table.name.lower():
                    score += 3.0
            if score > 0:
                scores[table.name] = score

        if len(scores) >= 2 or any(
            kw in q_lower for kw in ("join", "across", "between", "by region", "per ")
        ):
            return [t.name for t in schema.tables]

        ranked = sorted(scores.items(), key=lambda x: -x[1])
        if ranked:
            return [n for n, _ in ranked[:limit]]

        # Catalog-aware fallback: match description tokens when schema scoring is empty.
        if catalog and tokens:
            catalog_scores: dict[str, float] = {}
            for table in schema.tables:
                entry = catalog.get_entry(table.name, table.schema_name)
                if not entry:
                    continue
                desc = (catalog.get_description(entry) or "").lower()
                if not desc:
                    continue
                score = sum(5.0 for tok in tokens if tok in desc)
                if score > 0:
                    catalog_scores[table.name] = score
            if catalog_scores:
                ranked = sorted(catalog_scores.items(), key=lambda x: -x[1])
                return [n for n, _ in ranked[:limit]]

        return []

    def score_table(
        self,
        table: TableSchema,
        question: str,
        catalog: DataCatalogRegistry | None,
    ) -> float:
        mini_schema = DatabaseSchema(dialect="postgres", tables=[table])
        names = self.select_tables(
            question,
            mini_schema,
            catalog,
            max_tables=1,
        )
        return 10.0 if table.name in names else 0.0
