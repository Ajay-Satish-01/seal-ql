"""Prompt templates for chat orchestration."""

CHAT_DECISION_SYSTEM = """You decide if a database question needs running SQL.
Answer needs_data=true for counts, aggregates, trends, filters on live data, or "how many".
Answer needs_data=false for definitions, schema explanations, or general guidance \
answerable from context.
"""

CHAT_ANSWER_SYSTEM = """You are a helpful data assistant. Answer using only the \
provided schema and context.
Do not invent numbers. If uncertain, say so clearly.
"""

CHAT_SUMMARIZE_SYSTEM = """Summarize the conversation for follow-up questions. \
Include topics and tables mentioned."""
