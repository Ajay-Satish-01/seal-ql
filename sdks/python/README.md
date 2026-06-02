# Seal Python SDK

The official Python SDK for interacting with the Seal API.

**Docs:** [docs/README.md](../../docs/README.md) · embedding [docs/embedding.md](../../docs/embedding.md) · multi-database [docs/multi-database.md](../../docs/multi-database.md)

## Installation

```bash
pip install seal
```

Optional dependencies for dataframes:

```bash
pip install "seal[pandas]"
# or
pip install "seal[polars]"
```

## Synchronous Client

```python
from seal import Seal

# Pass api_key when the server sets SEAL_API_KEY (sent as the X-API-Key header).
with Seal("http://localhost:8000", api_key="your-secret") as client:
    schema = client.schema()
    print([t.name for t in schema.tables])

    result = client.query("Show me revenue by month")
    print(result.sql)
    print(result.results)

    catalog = client.catalog()
    print(catalog.tables)

    chat = client.chat(
        "What drove revenue last month?",
        include_charts=True,
        session_id="user-1",
    )
    print(chat.message, chat.sql)
```

## Chat streaming (SSE)

The first SSE event is `seal.meta` with a **flat** JSON payload (execution fields at the top level, not nested under `metadata`). See [docs/chat-metadata.md](../../docs/chat-metadata.md) for the full contract (`used_sql`, `enhancement`, `scope`, `refusal`, `sql_error`).

```python
for event in client.chat_stream("Summarize orders by region", include_charts=True):
    if event["type"] == "meta":
        print(event["data"].get("sql"))
    elif event["type"] == "meta_error":
        # Malformed seal.meta — partial session/database_id may still be present
        print("meta validation failed", event.get("data"))
    elif event["type"] == "delta":
        print(event["content"], end="", flush=True)
```

Non-streaming `client.chat()` returns nested `metadata` on `ChatResponse` (same fields as query `metadata`, plus chat-specific keys such as `scope`, `refusal`, and `suggested_queries` on guardrails refusals).

## Guardrails errors

Out-of-scope **query** requests return HTTP 400 with a structured FastAPI `detail` object:

```python
{
  "detail": {
    "detail": "query_out_of_scope",
    "reason": "off-topic pattern",
    "suggested_queries": ["Show order count by month", "What tables are available?"]
  }
}
```

The SDK raises `QueryOutOfScopeError` (subclass of `QueryError`) with `.reason` and `.suggested_queries`:

```python
from seal import QueryOutOfScopeError, Seal

try:
    client.query("write me a poem")
except QueryOutOfScopeError as e:
    print(e.reason, e.suggested_queries)
```

Out-of-scope **chat** returns HTTP 200 with `metadata.refusal=true` and `metadata.suggested_queries` (same field on SSE `seal.meta` when `stream=true`). Other structured chat 400s (e.g. `session_database_id_mismatch`) surface as `QueryError` with the API `message` text.

## Asynchronous Client

```python
import asyncio
from seal import AsyncSeal

async def main():
    async with AsyncSeal("http://localhost:8000", api_key="your-secret") as client:
        result = await client.query("Count all users")
        print(result.results)

        async for event in client.chat_stream("Hello"):
            if event["type"] == "delta":
                print(event["content"], end="")

asyncio.run(main())
```

## Multiple databases

When the API registers extra backends (`config/databases.yaml` or `SEAL_DATABASES`), pass `database_id` on query, chat, and schema:

```python
result = client.query("Total orders", database_id="default")
schema = client.schema(database_id="analytics")
reply = client.chat("What tables exist?", database_id="analytics")
```

## Working with DataFrames

```python
import pandas as pd

result = client.query("Top 10 products by revenue")
df = pd.DataFrame(result.results)
print(df.head())
```
