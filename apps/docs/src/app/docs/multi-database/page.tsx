import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { Callout } from '@/components/docs/callout';
import { CodeBlock } from '@/components/code-block';
import { DocsProse } from '@/components/docs/docs-prose';
import { SITE } from '@/lib/constants';
import { curlWithAuth } from '@/lib/doc-snippets';

export default function MultiDatabasePage() {
  const base = SITE.defaultBaseUrl;

  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Multi-database routing"
        description="Connect Seal to one or more SQL databases, then pick which one each request uses — explained from scratch with examples."
      />

      <DocsProse>
        <h2>What problem does this solve?</h2>
        <p>
          Seal turns natural language into SQL and runs it against <strong>your</strong> database.
          Most setups have one database (for example the Postgres container from{' '}
          <code>make up</code>). Some setups have <strong>more than one</strong> place data lives:
        </p>
        <ul>
          <li>Primary Postgres for orders + a DuckDB file for pre-aggregated analytics</li>
          <li>Operational DB + a read-only warehouse replica</li>
          <li>Dev database vs a local analytics sandbox</li>
        </ul>
        <p>
          <strong>Multi-database routing</strong> lets a single Seal API talk to several backends.
          You register each backend once at startup with a short name (an <em>id</em>). Every query,
          chat, or schema request can say which id to use.
        </p>

        <Callout variant="info" title="Only one database?">
          You do not need this page. Set <code>DATABASE_URL</code> in <code>.env</code> and use Seal
          normally — every request automatically uses id <code>&quot;default&quot;</code>. You can
          skip <code>database_id</code> in API calls entirely.
        </Callout>

        <h2>Core idea (read this first)</h2>
        <p>There are two separate steps. Do not mix them up:</p>
        <ol>
          <li>
            <strong>Server setup (you, once)</strong> — Tell Seal the real connection URLs. This
            happens in <code>.env</code> or <code>config/databases.yaml</code> when the API starts.
            Seal builds an internal registry: id → connection.
          </li>
          <li>
            <strong>Each API request (your app or SDK)</strong> — Pass a{' '}
            <code>database_id</code> string such as <code>&quot;default&quot;</code> or{' '}
            <code>&quot;analytics&quot;</code>. Seal looks up that id and runs SQL there.
          </li>
        </ol>
        <p>
          Clients never send Postgres passwords or JDBC URLs in JSON bodies. They only send ids that
          you already registered. That keeps credentials on the server.
        </p>

        <pre className="not-prose overflow-x-auto rounded-xl border border-border/50 bg-muted/30 p-5 font-mono text-xs leading-relaxed text-foreground">
          {`YOUR .env / databases.yaml          YOUR API REQUEST
─────────────────────────────          ────────────────────
DATABASE_URL →  id "default"    ←──    database_id: "default"
analytics url → id "analytics"  ←──    database_id: "analytics"
warehouse url → id "warehouse"  ←──    database_id: "warehouse"

Unknown id?  →  HTTP 404  unknown_database_id`}
        </pre>

        <h2>Which endpoints accept database_id?</h2>
        <p>
          Pass <code>database_id</code> on every call that runs SQL or introspects schema. The
          catalog endpoint is global (built from <code>default</code> only).
        </p>
        <ul>
          <li>
            <code>POST /v1/query</code> — JSON body <code>database_id</code>
          </li>
          <li>
            <code>POST /v1/chat</code> — JSON body <code>database_id</code> on{' '}
            <strong>each</strong> message (including follow-ups)
          </li>
          <li>
            <code>GET /v1/schema?database_id=</code> — query parameter
          </li>
          <li>
            Agent tools <code>seal_query</code>, <code>seal_chat</code>,{' '}
            <code>seal_get_schema</code> — tool argument <code>database_id</code>
          </li>
        </ul>
        <p>
          Confirm the backend in responses: <code>metadata.database_id</code> on query and chat JSON;
          the first <code>seal.meta</code> SSE event on streaming chat.
        </p>

        <h2>Connection URL formats</h2>
        <p>
          You register real connection strings in <code>.env</code> or{' '}
          <code>config/databases.yaml</code>. Clients only send short ids. Supported forms:
        </p>
        <ul>
          <li>
            <strong>Postgres</strong> —{' '}
            <code>postgresql+asyncpg://user:pass@host:5432/dbname</code> (same as{' '}
            <code>DATABASE_URL</code> in Docker)
          </li>
          <li>
            <strong>DuckDB file</strong> — <code>duckdb:///data/analytics.duckdb</code> (recommended
            URL style) or a plain path such as <code>/data/analytics.duckdb</code>
          </li>
          <li>
            <strong>DuckDB in-memory</strong> — <code>:memory:</code> for tests or ephemeral
            analytics
          </li>
        </ul>
        <Callout variant="info" title="DuckDB URL normalization">
          Seal accepts <code>duckdb:///path/to/file.duckdb</code> in config for consistency with
          Postgres-style URLs. At startup it converts that to the file path the DuckDB driver
          expects (for example <code>/path/to/file.duckdb</code>). Remote DuckDB hosts are not
          supported — only local files or <code>:memory:</code>.
        </Callout>
        <p>
          In Docker, mount a host directory into the API container so the file persists, for
          example <code>./data:/data</code> in Compose and{' '}
          <code>duckdb:///data/analytics.duckdb</code> in YAML.
        </p>

        <h2>Scenario A — Single database (simplest)</h2>
        <p>This is the default Docker / quickstart path.</p>
        <h3>1. Configure</h3>
        <CodeBlock
          language="bash"
          code={`# .env (already in .env.example)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/seal`}
        />
        <p>
          Seal registers exactly one entry: <code>default</code> → that URL. No extra files needed.
        </p>
        <h3>2. Ask a question (curl)</h3>
        <CodeBlock
          language="bash"
          code={curlWithAuth(base, 'POST', '/v1/query', {
            query: 'How many orders are there?',
          })}
        />
        <p>
          Omitting <code>database_id</code> is the same as sending{' '}
          <code>&quot;default&quot;</code>.
        </p>
        <h3>3. Same thing in Python</h3>
        <CodeBlock
          language="python"
          code={`from seal import Seal

with Seal("${base}", api_key="your-api-key") as client:
    # database_id optional — defaults to "default"
    result = client.query("How many orders are there?")
    print(result.sql)
    print(result.results)`}
        />

        <h2>Scenario B — Two databases (step by step)</h2>
        <p>
          Imagine you keep live orders in Postgres (<code>default</code>) and a DuckDB file with
          rolled-up metrics (<code>analytics</code>).
        </p>

        <h3>Step 1 — Keep your primary URL</h3>
        <CodeBlock
          language="bash"
          code={`# .env — unchanged; this ALWAYS becomes id "default"
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/seal`}
        />

        <h3>Step 2 — Register the second database</h3>
        <p>
          Copy <code>config/databases.example.yaml</code> to{' '}
          <code>config/databases.yaml</code> and add your extra id(s):
        </p>
        <CodeBlock
          language="yaml"
          code={`# config/databases.yaml
databases:
  analytics:
    url: duckdb:///data/analytics.duckdb`}
        />
        <p>
          Docker Compose already mounts <code>./config</code> into the API container (same as{' '}
          <code>catalog.yaml</code>). Alternatively, without a file:
        </p>
        <CodeBlock
          language="bash"
          code={`# .env — JSON map of id → connection URL (non-default ids only)
SEAL_DATABASES='{"analytics":"duckdb:///data/analytics.duckdb"}'`}
        />
        <Callout variant="warning" title="Do not override default in YAML/JSON">
          <code>DATABASE_URL</code> always owns the <code>default</code> id. If you put{' '}
          <code>default:</code> in <code>databases.yaml</code>, Seal ignores it and keeps using{' '}
          <code>DATABASE_URL</code>.
        </Callout>

        <h3>Step 3 — Restart the API</h3>
        <CodeBlock language="bash" code="make down && make up" />
        <p>
          On startup, logs show lines like{' '}
          <code>Registering database &apos;default&apos;</code> and{' '}
          <code>Registering database &apos;analytics&apos;</code>.
        </p>

        <h3>Step 4 — Query the primary database</h3>
        <CodeBlock
          language="bash"
          code={curlWithAuth(base, 'POST', '/v1/query', {
            query: 'Count orders by status',
            database_id: 'default',
          })}
        />
        <p>Example response shape (abbreviated):</p>
        <CodeBlock
          language="json"
          code={`{
  "sql": "SELECT status, COUNT(*) AS n FROM orders GROUP BY status LIMIT 10000",
  "columns": [{"name": "status", "type": "varchar"}, {"name": "n", "type": "int8"}],
  "results": [{"status": "shipped", "n": 42}],
  "chart": { "chart_type": "bar", "...": "..." },
  "metadata": {
    "database_id": "default",
    "row_count": 3,
    "execution_time_ms": 12.4
  }
}`}
        />

        <h3>Step 5 — Query the analytics database</h3>
        <CodeBlock
          language="bash"
          code={curlWithAuth(base, 'POST', '/v1/query', {
            query: 'Show daily revenue for the last 7 days',
            database_id: 'analytics',
          })}
        />
        <p>
          Same endpoint, different <code>database_id</code> — Seal introspects and executes against
          DuckDB instead of Postgres.
        </p>

        <h3>Step 6 — Inspect schema for each backend</h3>
        <CodeBlock
          language="bash"
          code={`# Tables in Postgres (default)
curl -s "${base}/v1/schema?database_id=default" \\
  -H "X-API-Key: your-api-key" | head

# Tables in DuckDB (analytics)
curl -s "${base}/v1/schema?database_id=analytics" \\
  -H "X-API-Key: your-api-key" | head`}
        />

        <h3>Step 7 — Chat against a specific database</h3>
        <p>
          Chat works the same way: pass <code>database_id</code> on every message. The server
          introspects that database before answering.
        </p>
        <CodeBlock
          language="bash"
          code={curlWithAuth(base, 'POST', '/v1/chat', {
            message: 'What tables do I have?',
            database_id: 'analytics',
          })}
        />
        <p>Example response (abbreviated):</p>
        <CodeBlock
          language="json"
          code={`{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "You have tables daily_revenue, product_rollups, ...",
  "sql": null,
  "metadata": {
    "database_id": "analytics",
    "scope": { "in_scope": true, "source": "heuristic" }
  }
}`}
        />
        <p>
          Follow-up messages reuse <code>session_id</code> for conversation memory.
        </p>

        <h3>Session pinning (important for chat)</h3>
        <p>Chat sessions can remember which database you used, with these rules:</p>
        <ol>
          <li>
            A <strong>new</strong> <code>session_id</code> accepts any registered{' '}
            <code>database_id</code>.
          </li>
          <li>
            After the first <strong>successful in-scope</strong> turn (SQL or conversational answer
            that completed normally), the session <strong>pins</strong> that{' '}
            <code>database_id</code>.
          </li>
          <li>
            Every follow-up must send the <strong>same</strong> <code>database_id</code>, or you
            get HTTP 400 with <code>session_database_id_mismatch</code>.
          </li>
          <li>
            <strong>Guardrail refusals</strong> (out-of-scope questions) do <em>not</em> pin the
            session — you can try again with a different <code>database_id</code> on the same{' '}
            <code>session_id</code> until a successful turn pins it.
          </li>
        </ol>
        <CodeBlock
          language="bash"
          code={`# First message — pins to analytics after success
${curlWithAuth(base, 'POST', '/v1/chat', {
  message: 'List tables',
  database_id: 'analytics',
})}

# Follow-up — MUST repeat database_id (use session_id from response)
${curlWithAuth(base, 'POST', '/v1/chat', {
  message: 'Describe the largest table',
  session_id: 'YOUR_SESSION_ID',
  database_id: 'analytics',
})}`}
        />

        <h3>Streaming chat</h3>
        <p>
          Set <code>stream: true</code> on <code>POST /v1/chat</code>. Pass{' '}
          <code>database_id</code> the same way. The first SSE event is{' '}
          <code>event: seal.meta</code> and includes <code>database_id</code>,{' '}
          <code>sql</code>, <code>chart</code>, and <code>sources</code> before token deltas. See{' '}
          <Link href="/docs/chat-streaming">Chat streaming</Link>.
        </p>
        <p>
          Session <code>database_id</code> mismatches return HTTP 400 <em>before</em> the stream
          starts (not mid-stream).
        </p>

        <h2>SDK examples (same ids)</h2>
        <h3>Python</h3>
        <CodeBlock
          language="python"
          code={`from seal import Seal

with Seal("${base}", api_key="your-api-key") as client:
    # Primary Postgres
    orders = client.query("Total orders today", database_id="default")

    # DuckDB analytics file
    revenue = client.query("Daily revenue trend", database_id="analytics")

    # Schema introspection per backend
    pg_schema = client.schema(database_id="default")
    duck_schema = client.schema(database_id="analytics")

    # Chat on analytics DB
    reply = client.chat("Summarize daily_revenue", database_id="analytics")
    print(reply.message)`}
        />
        <h3>TypeScript</h3>
        <CodeBlock
          language="typescript"
          code={`import { Seal } from 'seal';

const client = new Seal({
  baseUrl: '${base}',
  apiKey: 'your-api-key',
});

const orders = await client.query('Total orders today', 'default');
const revenue = await client.query('Daily revenue trend', 'analytics');
const schema = await client.schema({ databaseId: 'analytics' });
const chat = await client.chat('Summarize daily_revenue', { databaseId: 'analytics' });`}
        />
        <p>
          More SDK detail: <Link href="/docs/python-sdk">Python SDK</Link>,{' '}
          <Link href="/docs/typescript-sdk">TypeScript SDK</Link>.
        </p>

        <h2>What happens inside Seal (short version)</h2>
        <ol>
          <li>
            Request arrives with <code>database_id</code> (or <code>&quot;default&quot;</code> if
            omitted).
          </li>
          <li>
            <code>DatabaseRegistry</code> looks up the id. Missing id → 404{' '}
            <code>unknown_database_id</code>.
          </li>
          <li>
            Seal introspects <strong>that</strong> database&apos;s schema (tables, columns, keys).
          </li>
          <li>
            Guardrails → planner → SQL validation → execute — same pipeline as always, but against
            the chosen connection.
          </li>
          <li>
            Response includes <code>metadata.database_id</code> so you can confirm which backend
            ran.
          </li>
        </ol>
        <p>
          Full pipeline: <Link href="/docs/how-it-works">How Seal works</Link>.
        </p>

        <h2>Important limitations</h2>
        <p>
          These are shared across <strong>all</strong> registered ids in one Seal process today:
        </p>
        <ul>
          <li>
            <strong>Data catalog</strong> (<code>config/catalog.yaml</code>) — synced from the{' '}
            <code>default</code> database at startup. Descriptions may not match a different schema
            on <code>analytics</code>.
          </li>
          <li>
            <strong>Vector RAG</strong> — if enabled, the index is built from{' '}
            <code>default</code> only. Chat on non-default ids skips vector retrieval.
          </li>
          <li>
            <strong>Semantic metrics YAML</strong> — one global layer for the whole instance.
          </li>
        </ul>
        <p>
          If your databases have <strong>completely different schemas</strong>, the reliable pattern
          is <strong>one Seal container per database</strong> (each with its own{' '}
          <code>DATABASE_URL</code>). Your application picks which Seal URL to call — see{' '}
          <Link href="/docs/authentication">Authentication</Link> for the gateway pattern.
        </p>

        <h2>Agents and OpenAI-style tools</h2>
        <p>
          Download <code>seal-tools.openai.json</code> from{' '}
          <Link href="/docs/agent-frameworks">Agent frameworks</Link>. Tools accept{' '}
          <code>database_id</code> the same way as HTTP:
        </p>
        <CodeBlock
          language="json"
          code={`{
  "name": "seal_query",
  "arguments": {
    "query": "Monthly active users",
    "database_id": "analytics"
  }
}`}
        />

        <h2>HTTP errors you may see</h2>
        <ul>
          <li>
            <strong>404</strong> <code>unknown_database_id</code> — id not in registry (checked
            before guardrails on query). Fix config and restart the API.
          </li>
          <li>
            <strong>422</strong> — empty <code>database_id</code> (minimum length 1).
          </li>
          <li>
            <strong>400</strong> <code>session_database_id_mismatch</code> — chat follow-up used
            a different <code>database_id</code> than the pinned session. Use a new{' '}
            <code>session_id</code> or match the pinned id.
          </li>
          <li>
            <strong>400</strong> structured <code>query_out_of_scope</code> (with{' '}
            <code>suggested_queries</code>) — guardrails rejected the query
            (unrelated to database routing).
          </li>
        </ul>

        <h2>Troubleshooting</h2>
        <ul>
          <li>
            <strong>404</strong> <code>unknown_database_id</code> — typo in the request, or the id
            was never registered. Check <code>config/databases.yaml</code>,{' '}
            <code>SEAL_DATABASES</code>, and restart the API. Startup logs should list{' '}
            <code>Registering database &apos;…&apos;</code> for each id.
          </li>
          <li>
            <strong>DuckDB file not found / invalid database file</strong> — path not mounted in
            Docker, or pointing at a non-database file. Use <code>duckdb:///…</code> with a
            writable directory inside the container.
          </li>
          <li>
            <strong>SQL errors on non-default id</strong> — schema differs from what the planner
            expects; introspect with <code>GET /v1/schema?database_id=...</code> first. Catalog
            descriptions from <code>default</code> are not applied on non-default ids.
          </li>
          <li>
            <strong>Chat works on default but not analytics</strong> — confirm{' '}
            <code>metadata.database_id</code> in the response; vector RAG and catalog hints only
            apply to <code>default</code>.
          </li>
          <li>
            <strong>Wrong row counts vs your BI tool</strong> — confirm{' '}
            <code>metadata.database_id</code> in the response matches the DB you intended.
          </li>
        </ul>

        <h2>Configuration reference</h2>
        <p>
          Environment variables: <Link href="/docs/configuration#database">Database section</Link>{' '}
          (<code>DATABASE_URL</code>, <code>SEAL_DATABASES_PATH</code>,{' '}
          <code>SEAL_DATABASES</code>).
        </p>

        <p>
          Deployment patterns (one Seal per DB, BFF, multi-tenant):{' '}
          <Link href="/docs/embedding">Embedding Seal</Link>.
        </p>

        <Callout variant="info" title="For contributors">
          Implementation paths and registry code: <code>docs/multi-database.md</code> in the
          repository. Embedder overview: <code>docs/embedding.md</code>.
        </Callout>
      </DocsProse>
    </div>
  );
}
