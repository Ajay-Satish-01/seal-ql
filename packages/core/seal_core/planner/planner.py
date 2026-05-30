import logging
from typing import Any

import litellm

from seal_core.llm.client import (
    get_api_base,
    get_api_key,
    get_async_client,
    get_model,
)
from seal_core.planner.models import QueryPlan
from seal_core.planner.prompts import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_USER_PROMPT,
    REPAIR_SYSTEM_PROMPT,
)
from seal_core.schema.models import DatabaseSchema
from seal_core.settings import get_settings

logger = logging.getLogger(__name__)


class QueryPlanner:
    """
    LLM-powered query planner.
    Converts natural language questions into structured QueryPlan objects.
    Uses Instructor and LiteLLM for robust, schema-validated structured output.
    """

    def __init__(self, model: str | None = None, api_base: str | None = None) -> None:
        self.client = get_async_client()
        self.model = model or get_model()
        self.api_base = api_base or get_api_base()
        self.api_key = get_api_key()

    def _catalog_context(
        self,
        data_catalog: Any | None,
        table_names: list[str] | None,
    ) -> str:
        if data_catalog is None:
            return ""
        return data_catalog.to_prompt_context(table_names=table_names)

    def _schema_context(
        self,
        schema: DatabaseSchema,
        table_names: list[str] | None,
    ) -> str:
        if not table_names:
            return schema.to_prompt_context()
        tables = [t for t in schema.tables if t.name.lower() in {n.lower() for n in table_names}]
        subset = DatabaseSchema(
            dialect=schema.dialect,
            tables=tables,
            relationships=[
                r
                for r in schema.relationships
                if r.from_table.lower() in {n.lower() for n in table_names}
                or r.to_table.lower() in {n.lower() for n in table_names}
            ],
            has_timescaledb=schema.has_timescaledb,
        )
        return subset.to_prompt_context()

    async def generate_plan(
        self,
        schema: DatabaseSchema,
        question: str,
        semantic_registry: Any | None = None,
        data_catalog: Any | None = None,
        table_names: list[str] | None = None,
    ) -> QueryPlan:
        """
        Generates a QueryPlan for the given natural language question and database schema.

        Args:
            schema: The full database schema context.
            question: The user's natural language question.
            semantic_registry: Optional registry containing semantic metrics and dimensions.

        Returns:
            A fully structured QueryPlan containing the SQL, chart type, and metadata.

        Raises:
            Exception: If the LLM fails to generate a valid plan.
        """
        schema_context = self._schema_context(schema, table_names)
        semantic_context = ""
        if semantic_registry is not None:
            semantic_context = semantic_registry.get_context_string()
        catalog_context = self._catalog_context(data_catalog, table_names)

        system_prompt = PLANNER_SYSTEM_PROMPT.format(
            schema_context=schema_context,
            catalog_context=catalog_context,
            dialect=schema.dialect,
            semantic_context=semantic_context,
        )
        user_prompt = PLANNER_USER_PROMPT.format(question=question)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        logger.info(f"Generating QueryPlan using model {self.model} for question: {question}")

        # Instructor patches the client, allowing us to pass `response_model` directly.
        try:
            plan = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_model=QueryPlan,
                api_base=self.api_base,
                api_key=self.api_key,
                max_retries=get_settings().llm_max_retries,  # From centralized settings
            )
            return plan  # type: ignore
        except litellm.AuthenticationError as e:
            logger.error(f"Authentication Error with LLM: {e}")
            raise
        except litellm.RateLimitError as e:
            logger.error(f"Rate Limited by LLM provider: {e}")
            raise
        except litellm.APIError as e:
            logger.error(f"LLM API Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to generate QueryPlan: {str(e)}")
            raise

    async def repair_plan(
        self,
        question: str,
        original_sql: str,
        error_message: str,
        *,
        schema: DatabaseSchema | None = None,
        semantic_registry: Any | None = None,
        data_catalog: Any | None = None,
        table_names: list[str] | None = None,
    ) -> QueryPlan:
        """
        Attempts to repair a failed SQL query using the LLM.

        Args:
            question: The original user question.
            original_sql: The SQL query that failed validation or execution.
            error_message: The error message returned by the database or validator.

        Returns:
            A new, repaired QueryPlan.
        """
        extra = ""
        if schema is not None:
            catalog_context = self._catalog_context(data_catalog, table_names)
            semantic_context = ""
            if semantic_registry is not None:
                semantic_context = semantic_registry.get_context_string()
            extra = (
                f"\n\nSchema context:\n{self._schema_context(schema, table_names)}"
                f"{catalog_context}{semantic_context}"
            )

        system_prompt = (
            REPAIR_SYSTEM_PROMPT.format(
                question=question, original_sql=original_sql, error_message=error_message
            )
            + extra
        )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Please provide the fixed QueryPlan."},
        ]

        logger.info(f"Attempting to repair QueryPlan using model {self.model}")

        try:
            plan = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_model=QueryPlan,
                api_base=self.api_base,
                api_key=self.api_key,
                max_retries=get_settings().llm_max_retries,
            )
            return plan  # type: ignore
        except litellm.AuthenticationError as e:
            logger.error(f"Authentication Error with LLM: {e}")
            raise
        except litellm.RateLimitError as e:
            logger.error(f"Rate Limited by LLM provider: {e}")
            raise
        except litellm.APIError as e:
            logger.error(f"LLM API Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to repair QueryPlan: {str(e)}")
            raise
