# Intelligence Connector Python SDK

The official Python SDK for interacting with the Intelligence Connector API.

## Installation

```bash
pip install intelligence-connector-sdk
```

Optional dependencies for dataframes:
```bash
pip install "intelligence-connector-sdk[pandas]"
# or
pip install "intelligence-connector-sdk[polars]"
```

## Synchronous Client

```python
from intelligence_connector import IntelligenceConnector

with IntelligenceConnector("http://localhost:8000") as client:
    # 1. Fetch Schema
    schema = client.schema()
    print([t.name for t in schema.tables])

    # 2. Query
    result = client.query("Show me revenue by month")
    print(result.sql)
    print(result.results)
```

## Asynchronous Client

```python
import asyncio
from intelligence_connector import AsyncIntelligenceConnector

async def main():
    async with AsyncIntelligenceConnector("http://localhost:8000") as client:
        result = await client.query("Count all users")
        print(result.results)

asyncio.run(main())
```

## Working with DataFrames

If you have `pandas` or `polars` installed, you can easily convert the API response into a dataframe (server-side, this uses DuckDB or Postgres bindings):

```python
# Assuming you fetched a query response as `result`
# If you don't use the SDK, you can manually initialize the model:
# from intelligence_connector.models import QueryResponse
# result = QueryResponse.model_validate(json_dict)

# Wait, `QueryResponse` from the API doesn't have `to_pandas` method directly
# The raw SDK only returns raw python dicts.
# However, if you are running the Intelligence Core package locally via `intelligence_sql`,
# you can use `QueryResult.to_pandas()`. For the HTTP SDK, you load it manually:

import pandas as pd
df = pd.DataFrame(result.results)
print(df.head())
```
