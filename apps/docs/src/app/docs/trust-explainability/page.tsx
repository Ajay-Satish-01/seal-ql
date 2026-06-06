import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { Callout } from '@/components/docs/callout';
import { CodeBlock } from '@/components/code-block';
import { DocLink } from '@/components/docs/doc-link';
import { DocsProse } from '@/components/docs/docs-prose';
import { ConfigReference } from '@/components/docs/config-reference';

const trustConfig = [
  {
    name: 'SEAL_TRUST_EXPLAINABILITY_ENABLED',
    type: 'bool',
    default: 'false',
    description:
      'Master toggle. When true, responses include SQL provenance (tables_used, columns_used, catalog_matches), sources, scope decisions, and repair_attempts. When false, these fields are stripped from all API responses and SSE events.',
    expect:
      'With true: query and chat responses include sql, sources, tables_used, columns_used, catalog_matches, scope, repair_attempts. Dashboard shows the Trust & explainability panel with all five tabs.',
  },
  {
    name: 'STRICT_STREAM_META_VALIDATION',
    type: 'bool',
    default: 'false',
    description:
      'When true, requests fail if metadata or seal.meta events fail contract validation. Default logs a warning only.',
    expect:
      'With true: malformed metadata causes HTTP 500. With false (default): a warning is logged and the request succeeds.',
  },
];

export default function TrustExplainabilityPage() {
  return (
    <div className="w-full">
      <PageHeader
        title="Trust & explainability"
        description="Understand exactly how Seal answered every question — SQL provenance, catalog matches, guardrails scope, repair history, and execution metrics."
      />

      <DocsProse>
        <p>
          Trust &amp; explainability gives operators and end-users full visibility into <em>how</em>{' '}
          Seal arrived at each answer. Every query and chat turn can expose the generated SQL, which
          tables and columns were referenced, how those tables matched the data catalog, whether
          guardrails flagged the request, how many SQL repair attempts occurred, and detailed
          execution metrics — all controlled by a single environment variable.
        </p>

        <Callout variant="success" title="Enable it">
          Set <code>SEAL_TRUST_EXPLAINABILITY_ENABLED=true</code> in your <code>.env</code> or via{' '}
          <Link href="/docs/workspace">workspace settings</Link>. The dashboard and SDKs
          automatically surface all explainability fields when enabled.
        </Callout>

        <h2>What gets exposed</h2>
        <p>
          When trust explainability is enabled, the following fields appear on API responses, SSE{' '}
          <code>seal.meta</code> events, and persisted session history:
        </p>

        <div className="not-prose my-6 grid gap-4 sm:grid-cols-2">
          <div className="border-border/50 rounded-xl border p-5">
            <h3 className="text-foreground mb-2 font-semibold">SQL &amp; sources</h3>
            <ul className="text-muted-foreground list-disc space-y-1.5 pl-5 text-sm">
              <li>
                <code>sql</code> — the exact SQL that was generated and executed
              </li>
              <li>
                <code>sources</code> — list of table names the planner identified as relevant
              </li>
              <li>
                <code>results</code> — preview rows from the executed query
              </li>
              <li>
                <code>columns</code> — typed column descriptors (name, type, nullable)
              </li>
            </ul>
          </div>
          <div className="border-border/50 rounded-xl border p-5">
            <h3 className="text-foreground mb-2 font-semibold">Provenance</h3>
            <ul className="text-muted-foreground list-disc space-y-1.5 pl-5 text-sm">
              <li>
                <code>tables_used</code> — tables actually referenced in the generated SQL
              </li>
              <li>
                <code>columns_used</code> — columns referenced in SELECT, WHERE, JOIN, etc.
              </li>
              <li>
                <code>catalog_matches</code> — catalog entries matched to the query, including
                schema name, table name, and business description
              </li>
            </ul>
          </div>
          <div className="border-border/50 rounded-xl border p-5">
            <h3 className="text-foreground mb-2 font-semibold">Scope &amp; guardrails</h3>
            <ul className="text-muted-foreground list-disc space-y-1.5 pl-5 text-sm">
              <li>
                <code>scope.in_scope</code> — whether the query was classified as in-scope
              </li>
              <li>
                <code>scope.source</code> — which stage decided:{' '}
                <code>heuristic</code>, <code>llm</code>, <code>limits</code>, or{' '}
                <code>disabled</code>
              </li>
              <li>
                <code>scope.reason</code> — human-readable classification reason
              </li>
              <li>
                <code>repair_attempts</code> — how many times the planner retried SQL generation
              </li>
            </ul>
          </div>
          <div className="border-border/50 rounded-xl border p-5">
            <h3 className="text-foreground mb-2 font-semibold">Execution metrics</h3>
            <ul className="text-muted-foreground list-disc space-y-1.5 pl-5 text-sm">
              <li>
                <code>execution_time_ms</code> — SQL execution time in milliseconds
              </li>
              <li>
                <code>row_count</code> — number of rows returned
              </li>
              <li>
                <code>truncated</code> — whether results were truncated by LIMIT
              </li>
              <li>
                <code>warnings</code> — any SQL validation warnings
              </li>
              <li>
                <code>enhancement</code> — which prompt enhancement steps ran (schema, vector
                RAG, summary)
              </li>
            </ul>
          </div>
        </div>

        <h2>How it works</h2>
        <p>
          Trust gating is applied at the API layer, not the pipeline. The planner, guardrails,
          and enhancement stages always produce full metadata internally. When{' '}
          <code>SEAL_TRUST_EXPLAINABILITY_ENABLED=false</code> (the default), trust-sensitive
          fields are <strong>stripped</strong> from responses before they reach the client:
        </p>
        <pre className="not-prose overflow-x-auto rounded-xl border border-border/50 bg-muted/30 p-5 font-mono text-xs leading-relaxed text-foreground">
          {`Pipeline generates full metadata
    │
    ▼
Trust gating layer (seal_core/pipeline/trust.py)
    │
    ├── SEAL_TRUST_EXPLAINABILITY_ENABLED=true
    │       → all fields pass through
    │
    └── SEAL_TRUST_EXPLAINABILITY_ENABLED=false
            → strips: sql, sources, results, columns
            → strips metadata: tables_used, columns_used,
              catalog_matches, repair_attempts, scope`}
        </pre>
        <p>
          This means you can run the same deployment with trust off for end-users (no SQL leakage)
          and flip it on for operators/debugging without restarting the API — toggle via{' '}
          <Link href="/docs/workspace">workspace settings</Link> with hot-reload.
        </p>

        <h2>API response examples</h2>
        <h3>Query — POST /v1/query</h3>
        <p>
          With trust enabled, the query response includes <code>sql</code>, <code>sources</code>,
          and full <code>metadata</code> with provenance:
        </p>
        <CodeBlock
          language="bash"
          code={`curl -s -X POST http://localhost:8000/v1/query \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: your-api-key" \\
  -d '{"query":"How many orders per month?"}' | jq '{
    sql,
    sources,
    metadata: {
      tables_used: .metadata.tables_used,
      columns_used: .metadata.columns_used,
      catalog_matches: .metadata.catalog_matches,
      repair_attempts: .metadata.repair_attempts,
      execution_time_ms: .metadata.execution_time_ms,
      row_count: .metadata.row_count
    }
  }'`}
        />
        <CodeBlock
          language="json"
          code={`{
  "sql": "SELECT date_trunc('month', created_at) AS month, COUNT(*) AS order_count FROM orders GROUP BY 1 ORDER BY 1",
  "sources": ["orders"],
  "metadata": {
    "tables_used": ["orders"],
    "columns_used": ["created_at"],
    "catalog_matches": [
      {
        "name": "orders",
        "schema": "public",
        "description": "Customer purchase orders with timestamps and amounts"
      }
    ],
    "repair_attempts": 0,
    "execution_time_ms": 12.4,
    "row_count": 6
  }
}`}
        />

        <h3>Chat SSE — seal.meta event</h3>
        <p>
          The first SSE event on a streaming chat response carries explainability data. With trust
          enabled, <code>seal.meta</code> includes all provenance fields at the top level:
        </p>
        <CodeBlock
          language="json"
          code={`{
  "session_id": "a1b2c3d4-...",
  "sources": ["orders", "customers"],
  "sql": "SELECT c.name, SUM(o.amount) AS total FROM orders o JOIN customers c ON o.customer_id = c.id GROUP BY 1 ORDER BY 2 DESC LIMIT 10",
  "tables_used": ["orders", "customers"],
  "columns_used": ["name", "amount", "customer_id", "id"],
  "catalog_matches": [
    { "name": "orders", "schema": "public", "description": "Customer purchase orders" },
    { "name": "customers", "schema": "public", "description": "Registered customer accounts" }
  ],
  "scope": {
    "in_scope": true,
    "source": "heuristic",
    "reason": "Data analytics question about orders"
  },
  "repair_attempts": 0,
  "execution_time_ms": 18.7,
  "row_count": 10,
  "used_sql": true,
  "enhancement": {
    "enabled": true,
    "applied": ["schema_context", "catalog_descriptions"]
  }
}`}
        />

        <h3>Session history — persisted explainability</h3>
        <p>
          When using <code>CHAT_SESSION_STORE=postgres</code>, explainability data is persisted
          alongside each assistant message. Loading a past session returns the same SQL, sources,
          metadata, chart, and results that were available when the turn was originally generated:
        </p>
        <CodeBlock
          language="bash"
          code={`# Get a session with explainability
curl -s http://localhost:8000/v1/chat/sessions/YOUR_SESSION_ID \\
  -H "X-API-Key: your-api-key" | jq '.messages[-1].explainability'`}
        />
        <CodeBlock
          language="json"
          code={`{
  "sql": "SELECT region, COUNT(*) AS order_count FROM orders GROUP BY region ORDER BY order_count DESC",
  "sources": ["orders"],
  "metadata": { "used_sql": true, "repair_attempts": 0, "tables_used": ["orders"] },
  "chart": { "mark": "bar", "encoding": { "x": { "field": "region" }, "y": { "field": "order_count" } } },
  "results": [
    { "region": "North America", "order_count": 1523 },
    { "region": "Europe", "order_count": 987 }
  ]
}`}
        />

        <Callout variant="info" title="Trust gating on session reads">
          When <code>SEAL_TRUST_EXPLAINABILITY_ENABLED=false</code>, loading a past session strips
          trust fields from stored explainability — the same gating that applies to live responses.
          If the stored explainability has no remaining content after gating, the field is omitted
          entirely (returns <code>null</code>) rather than an empty shell.
        </Callout>

        <h2>Dashboard explainability panel</h2>
        <p>
          The operational dashboard (<Link href="/docs/dashboard">port 3001</Link>) renders
          explainability as a tabbed panel with five sections:
        </p>
        <ul>
          <li>
            <strong>SQL</strong> — the generated SQL query, syntax-highlighted
          </li>
          <li>
            <strong>Sources</strong> — tables identified by the planner, displayed as labeled cards
          </li>
          <li>
            <strong>Provenance</strong> — catalog matches with descriptions, tables in SQL, and
            columns referenced. Each catalog match shows the schema-qualified name and its
            business description from the catalog
          </li>
          <li>
            <strong>Scope</strong> — guardrails verdict (in-scope/out-of-scope with source and
            reason), SQL repair attempts with explanation, refusal status, enhancement pipeline
            steps, and suggested alternative queries
          </li>
          <li>
            <strong>Metadata</strong> — execution time, row count, truncation status, warnings,
            and the full raw JSON payload
          </li>
        </ul>
        <p>
          On the <strong>Query</strong> page, the panel appears inline below results. On the{' '}
          <strong>Chat</strong> page, each assistant message has an <em>Explainability</em> button
          that opens a dialog with the same tabbed view for that specific turn.
        </p>

        <Callout variant="info" title="Per-turn explainability in chat">
          Each chat turn captures its own explainability snapshot. Different turns may use
          different tables, produce different SQL, or hit different guardrails paths. The
          explainability button on each message shows the data for <em>that specific turn</em>,
          not a global summary.
        </Callout>

        <h2>SDK usage</h2>
        <h3>Python</h3>
        <CodeBlock
          language="python"
          code={`from seal import Seal

client = Seal(base_url="http://localhost:8000", api_key="your-api-key")

# Query with full metadata
result = client.query("Orders by region last month")
print(f"SQL: {result.sql}")
print(f"Sources: {result.sources}")
print(f"Tables used: {result.metadata.get('tables_used')}")
print(f"Catalog matches: {result.metadata.get('catalog_matches')}")
print(f"Repair attempts: {result.metadata.get('repair_attempts')}")
print(f"Execution time: {result.metadata.get('execution_time_ms')}ms")

# Chat with explainability in session history
resp = client.chat("What are the top products?", include_charts=True)
print(f"Scope: {resp.metadata.get('scope')}")

# Load session to review past explainability
import requests
session = requests.get(
    f"http://localhost:8000/v1/chat/sessions/{resp.session_id}",
    headers={"X-API-Key": "your-api-key"}
).json()
for msg in session["messages"]:
    if msg.get("explainability"):
        print(f"Turn SQL: {msg['explainability']['sql']}")`}
        />

        <h3>TypeScript</h3>
        <CodeBlock
          language="typescript"
          code={`import { Seal } from 'seal';

const client = new Seal({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your-api-key',
});

// Query with full metadata
const result = await client.query('Orders by region last month');
console.log('SQL:', result.sql);
console.log('Sources:', result.sources);
console.log('Tables used:', result.metadata?.tables_used);
console.log('Catalog matches:', result.metadata?.catalog_matches);
console.log('Repair attempts:', result.metadata?.repair_attempts);
console.log('Execution time:', result.metadata?.execution_time_ms, 'ms');

// Streaming chat with explainability
for await (const event of client.chatStream({
  message: 'Top customers by revenue',
  include_charts: true,
})) {
  if (event.type === 'meta') {
    console.log('Scope:', event.data.scope);
    console.log('Sources:', event.data.sources);
    console.log('SQL:', event.data.sql);
    console.log('Catalog matches:', event.data.catalog_matches);
  }
}`}
        />

        <h2>Configuration</h2>
        <ConfigReference rows={trustConfig} />

        <Callout variant="warning" title="Security consideration">
          With trust explainability enabled, your API responses include generated SQL, table names,
          column names, and catalog descriptions. In production, only enable this for internal
          operator dashboards behind authentication — not for end-user-facing interfaces where
          schema leakage is a concern. Use the{' '}
          <Link href="/docs/embedding">BFF pattern</Link> to keep trust fields server-side while
          exposing only answers to end users.
        </Callout>

        <h2>Catalog matches explained</h2>
        <p>
          <code>catalog_matches</code> connect the planner&apos;s table selection to your{' '}
          <Link href="/docs/data-catalog">data catalog</Link>. For each table the planner
          identified as relevant to the query, Seal looks up its catalog entry and returns:
        </p>
        <ul>
          <li>
            <code>name</code> — table or view name
          </li>
          <li>
            <code>schema</code> — PostgreSQL schema (e.g. <code>public</code>)
          </li>
          <li>
            <code>description</code> — the business description from <code>catalog.yaml</code> or
            workspace overrides. <code>null</code> if no description is set
          </li>
        </ul>
        <p>
          Better catalog descriptions lead to better SQL generation. If a match shows{' '}
          <em>No description in catalog</em> in the dashboard, consider adding a description via{' '}
          <code>PATCH /v1/catalog/descriptions</code> or the dashboard Catalog editor.
        </p>

        <h2>Repair attempts explained</h2>
        <p>
          When the planner generates SQL that fails validation or execution (wrong column name,
          syntax error, schema mismatch), the error message is fed back to the LLM and it retries.
          The <code>repair_attempts</code> counter shows how many retries occurred:
        </p>
        <ul>
          <li>
            <strong>0</strong> — SQL passed validation on the first attempt (ideal)
          </li>
          <li>
            <strong>1–3</strong> — the planner self-corrected after initial errors
          </li>
          <li>
            <strong>Maximum</strong> — controlled by <code>LLM_MAX_RETRIES</code> (default 3).
            If all attempts fail, the turn returns <code>sql_error: true</code> with no SQL
          </li>
        </ul>
        <p>
          High repair counts on specific queries may indicate missing catalog descriptions,
          ambiguous column names, or schema changes the LLM hasn&apos;t adapted to.
        </p>

        <h2>Related</h2>
        <ul>
          <li>
            <DocLink href="/docs/execution-metadata">Execution metadata</DocLink> — full field
            reference for query and chat metadata
          </li>
          <li>
            <DocLink href="/docs/guardrails">Guardrails</DocLink> — how scope classification
            works
          </li>
          <li>
            <DocLink href="/docs/data-catalog">Data catalog</DocLink> — improving catalog
            descriptions for better provenance
          </li>
          <li>
            <DocLink href="/docs/chat-qa">Chat &amp; Q&amp;A</DocLink> — session memory and
            explainability persistence
          </li>
          <li>
            <DocLink href="/docs/dashboard">Dashboard</DocLink> — visual explainability panels
          </li>
          <li>
            <DocLink href="/docs/configuration">Configuration</DocLink> — all environment
            variables
          </li>
        </ul>
      </DocsProse>
    </div>
  );
}
