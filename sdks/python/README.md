# Seal Python SDK

The official Python SDK for interacting with the Seal API.

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
```

## Asynchronous Client

```python
import asyncio
from seal import AsyncSeal

async def main():
    async with AsyncSeal("http://localhost:8000", api_key="your-secret") as client:
        result = await client.query("Count all users")
        print(result.results)

asyncio.run(main())
```

## Working with DataFrames

```python
import pandas as pd

result = client.query("Top 10 products by revenue")
df = pd.DataFrame(result.results)
print(df.head())
```
