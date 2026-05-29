# Intelligence Connector TypeScript SDK

The official TypeScript SDK for interacting with the Intelligence Connector API.

## Installation

```bash
npm install intelligence-sdk
# or
yarn add intelligence-sdk
# or
pnpm add intelligence-sdk
```

## Basic Usage

```typescript
import { IntelligenceConnector } from 'intelligence-sdk';

const client = new IntelligenceConnector({
  baseUrl: 'http://localhost:8000',
});

async function run() {
  // 1. Get database schema
  const schema = await client.schema();
  console.log(
    'Tables:',
    schema.tables.map((t) => t.name),
  );

  // 2. Query data with natural language
  const response = await client.query('Show me daily active users for the last 30 days');

  console.log('SQL executed:', response.sql);
  console.log('Results:', response.results);
}
run();
```

## React Integration

The SDK ships with an optional React component to effortlessly render Vega-Lite charts returned by the API.

### Peer Dependencies

To use the React component, you must install the required peer dependencies:

```bash
npm install react react-dom vega vega-lite vega-embed
```

### Usage

```tsx
import React, { useState } from 'react';
import { IntelligenceConnector, VegaChart } from 'intelligence-sdk';

const client = new IntelligenceConnector({ baseUrl: 'http://localhost:8000' });

export function Dashboard() {
  const [result, setResult] = useState(null);

  const handleQuery = async () => {
    const data = await client.query('Revenue by month as a bar chart');
    setResult(data);
  };

  return (
    <div>
      <button onClick={handleQuery}>Ask Question</button>

      {result && result.chart?.chart_type !== 'table' && (
        <VegaChart spec={result.chart} theme="light" actions={true} />
      )}
    </div>
  );
}
```
