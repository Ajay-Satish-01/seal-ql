import type { ConfigRow } from '@/components/docs/config-reference';

export const databaseConfig: ConfigRow[] = [
  {
    name: 'DATABASE_URL',
    type: 'string',
    default: 'postgresql+asyncpg://…',
    description:
      'Primary analytics database. Always registered as database_id "default" for introspection, catalog sync, and SQL execution.',
    expect:
      'On startup, `/health` reports ready and `/v1/schema` lists tables from this database. Connection errors appear in API logs.',
  },
  {
    name: 'SEAL_DATABASES_PATH',
    type: 'string',
    default: 'config/databases.yaml',
    description:
      'Optional YAML file with a top-level `databases:` map (id → url string or {url: "…"}). If the file is missing, Seal uses only DATABASE_URL. Entries named `default` in YAML are ignored.',
    expect:
      'On restart, logs show `Registering database` for each id. Requests with that database_id introspect and execute on the configured backend. Unknown ids → HTTP 404. DuckDB URLs like duckdb:///data/file.duckdb are normalized to file paths.',
  },
  {
    name: 'SEAL_DATABASES',
    type: 'JSON string',
    description:
      'Optional env override: JSON object mapping database_id to a connection URL or {"url":"…"}. Merges with SEAL_DATABASES_PATH; cannot override `default`. Example: {"analytics":"duckdb:///data/analytics.duckdb"}.',
    expect:
      'Same routing behavior as SEAL_DATABASES_PATH. Useful in Docker when you prefer env over mounting databases.yaml. See /docs/multi-database for URL formats and chat session pinning.',
  },
  {
    name: 'DUCKDB_PATH',
    type: 'string',
    default: ':memory:',
    description:
      'Optional DuckDB path when you route specific workloads to DuckDB instead of Postgres. Most deployments use Postgres only.',
    expect:
      'Only relevant when your integration explicitly targets DuckDB; otherwise unused.',
  },
  {
    name: 'POSTGRES_*',
    type: 'compose',
    description:
      'User, password, database name, and host port for the bundled Postgres service in Docker Compose — not read directly by the API except via composed DATABASE_URL.',
    expect:
      'First `docker compose up` creates the database; `make seed` loads sample tables used by quickstart and the interactive demo fixtures.',
  },
];

export const authConfig: ConfigRow[] = [
  {
    name: 'SEAL_API_KEY',
    type: 'string',
    required: true,
    description:
      'Required at startup. Clients send this value as the `X-API-Key` header on every `/v1/*` call; missing or wrong keys receive HTTP 401.',
    expect:
      'SDKs and curl examples include the header automatically when you export this variable. The dashboard Settings page stores the same value in browser local storage for live API calls.',
  },
  {
    name: 'SEAL_DEV_MODE',
    type: 'boolean',
    default: 'true (.env.example)',
    description:
      'Enables immediate workspace hot-reload on PATCH. Must be false in production.',
    expect:
      'With `true`, workspace settings from the dashboard apply to the running API without `POST …/settings/apply`. With `false`, persisted changes sit in `pending_apply` until you apply or restart (see Workspace settings).',
  },
  {
    name: 'SEAL_DISABLE_DOCS',
    type: 'boolean',
    default: 'false',
    description:
      'Hides Swagger UI and the OpenAPI JSON route on the API process — useful when the API is internet-facing.',
    expect:
      'Browsing `/docs` on port 8000 returns 404; SDKs and your own OpenAPI copy are unaffected.',
  },
];

export const catalogConfig: ConfigRow[] = [
  {
    name: 'DATA_CATALOG_PATH',
    type: 'path',
    default: 'config/catalog.yaml',
    description:
      'YAML file describing tables, columns, and relationships. Shared by `/v1/query` and `/v1/chat` — the catalog is global, not per session.',
    expect:
      'After sync, the file on disk reflects live DDL plus any description overrides re-applied from workspace storage. Mount `./config` in Docker so edits survive container recreation.',
  },
  {
    name: 'CATALOG_AUTO_SYNC',
    type: 'boolean',
    default: 'true',
    description:
      'Regenerate the catalog from database introspection when the API starts (and when you call `POST /v1/catalog/sync`).',
    expect:
      'New tables appear in catalog and chat context without hand-editing YAML. User-written descriptions from the dashboard are preserved across sync.',
  },
  {
    name: 'CATALOG_PRUNE_REMOVED',
    type: 'boolean',
    default: 'true',
    description:
      'Remove catalog entries for tables that no longer exist in the database after a sync.',
    expect:
      'Dropped tables disappear from `/v1/catalog` and from planner context; stale entries do not linger in YAML.',
  },
  {
    name: 'DATA_CATALOG_STRICT',
    type: 'boolean',
    default: 'false',
    description:
      'When true, the planner must only reference catalog-known tables — stricter grounding, fewer hallucinated table names.',
    expect:
      'Out-of-catalog table references fail earlier in the pipeline with validation errors instead of invalid SQL.',
  },
  {
    name: 'WORKSPACE_STORE',
    type: 'string',
    default: 'postgres',
    description:
      'Where dashboard and API persist workspace settings and catalog description overrides: `postgres` (default) or `file` for tests.',
    expect:
      'With `postgres`, rows live in `seal_app.workspace_kv` after `migrate_app.sql`. With `file`, only `config/workspace.json` is used — no dashboard writes to a shared DB.',
  },
];

export const guardrailsConfig: ConfigRow[] = [
  {
    name: 'GUARDRAILS_ENABLED',
    type: 'boolean',
    default: 'true',
    description:
      'Master switch for the scope gate on `/v1/query` and `/v1/chat`. When false, all prompts reach the planner (not recommended in production).',
    expect:
      'Off-topic chat still returns HTTP 200 but may run SQL paths; query accepts any natural language. Useful only in controlled test environments.',
  },
  {
    name: 'GUARDRAILS_FAIL_CLOSED',
    type: 'boolean',
    default: 'true',
    description:
      'Treat LLM classifier failures (timeouts, provider errors) as out-of-scope instead of allowing the request through.',
    expect:
      'During provider outages, users see refusals or `query_out_of_scope` rather than unscoped SQL generation. Safer default for production.',
  },
  {
    name: 'MAX_QUERY_CHARS',
    type: 'integer',
    default: '4000',
    description: 'Hard limit on `/v1/query` prompt length before heuristics or the classifier run.',
    expect: 'Oversized bodies receive HTTP 400 with a validation detail before any LLM call.',
  },
  {
    name: 'MAX_CHAT_MESSAGE_CHARS',
    type: 'integer',
    default: '8000',
    description: 'Per-message character cap for chat user content.',
    expect: 'Long pasted documents are rejected at the API boundary; streaming is unaffected for valid sizes.',
  },
  {
    name: 'MAX_CHAT_HISTORY_CHARS',
    type: 'integer',
    default: '32000',
    description: 'Total character budget across chat history when enhancement summarizes older turns.',
    expect:
      'Very long sessions compress older messages; recent turns stay verbatim per `CHAT_RECENT_MESSAGES`.',
  },
];

export const chatConfig: ConfigRow[] = [
  {
    name: 'CHAT_ENHANCEMENT_ENABLED',
    type: 'boolean',
    default: 'true',
    description:
      'Enables the enhancement chain: schema focus, optional vector RAG, and multi-turn summarization before the answer LLM.',
    expect:
      'With `false`, chat behaves like a thinner Q&A path — faster, less context, no RAG retrieval step. Good when your agent already supplies schema.',
  },
  {
    name: 'STRICT_STREAM_META_VALIDATION',
    type: 'boolean',
    default: 'false',
    description:
      'When true, invalid chat metadata (JSON) or seal.meta (SSE) payloads raise instead of only logging a warning. Alias: STRICT_METADATA_VALIDATION.',
    expect:
      'Use in CI or staging to catch contract regressions early. Default off so production stays resilient to minor shape drift.',
  },
  {
    name: 'CHAT_SESSION_STORE',
    type: 'string',
    default: 'memory',
    description:
      'Chat session backend: `memory` (in-process, TTL) or `postgres` (persistent `seal_app.chat_sessions`). Alias: `MEMORY_BACKEND` (`sql` → postgres).',
    expect:
      'Use `postgres` on Lambda and multi-task ECS. Run `scripts/migrate_app.sql`. Dashboard lists sessions via `GET /v1/chat/sessions`.',
  },
  {
    name: 'CHAT_SESSION_STORE_CLASS',
    type: 'string',
    default: '(empty)',
    description:
      'Optional dotted import path for a custom `BaseSessionStore` implementation (advanced). When set, overrides `CHAT_SESSION_STORE`. Constructor may accept `database_url` or `settings`.',
    expect: 'Leave unset unless you ship a custom store class on `PYTHONPATH`.',
  },
  {
    name: 'CHAT_SESSION_DATABASE_URL',
    type: 'string',
    default: '(falls back to DATABASE_URL)',
    description:
      'Postgres connection URL for `CHAT_SESSION_STORE=postgres`. Allows DuckDB-primary deployments to point chat history at a separate Postgres instance.',
    expect:
      'Set when your `DATABASE_URL` is DuckDB but you want persistent chat sessions. The session store creates tables in the `seal_app` schema of this database.',
  },
  {
    name: 'CHAT_SESSION_LIST_DEFAULT_LIMIT',
    type: 'integer',
    default: '50',
    description: 'Default page size for `GET /v1/chat/sessions` when `limit` is omitted.',
    expect: 'Dashboard sidebar uses the API default unless a `limit` query param is set.',
  },
  {
    name: 'CHAT_SESSION_LIST_MAX_LIMIT',
    type: 'integer',
    default: '200',
    description: 'Maximum allowed `limit` query param on session list.',
    expect: 'Requests above this return HTTP 422.',
  },
  {
    name: 'CHAT_SESSION_TTL_SECONDS',
    type: 'integer',
    default: '3600',
    description: 'In-memory session TTL only (`CHAT_SESSION_STORE=memory`). Ignored for postgres.',
    expect:
      'After TTL, the same `session_id` starts a fresh conversation when using the memory backend.',
  },
  {
    name: 'CHAT_MAX_HISTORY_MESSAGES',
    type: 'integer',
    default: '20',
    description: 'Upper bound on stored messages per session before summarization kicks in.',
    expect:
      'Older turns roll into a summary block; the UI still shows recent messages from the API response, not the full raw history.',
  },
  {
    name: 'CHAT_RECENT_MESSAGES',
    type: 'integer',
    default: '6',
    description: 'How many latest turns stay verbatim when building the answer-stage prompt.',
    expect:
      'Follow-up questions like “filter that to Q3” retain nearby context; ancient turns are summarized only.',
  },
  {
    name: 'CHAT_ANSWER_PREVIEW_ROWS',
    type: 'integer',
    default: '20',
    description: 'SQL result rows included as grounding for the final chat answer LLM.',
    expect:
      'Answers cite actual row values from the preview; very wide result sets are truncated for token limits, not silently invented.',
  },
  {
    name: 'CHAT_MAX_CONTEXT_TABLES',
    type: 'integer',
    default: '8',
    description: 'Maximum tables injected into focused schema context for a single chat turn.',
    expect:
      'Large schemas prioritize the most relevant tables from retrieval; rarely-used tables may be omitted unless the user names them.',
  },
];

export const querySafetyConfig: ConfigRow[] = [
  {
    name: 'MAX_ROWS',
    type: 'integer',
    default: '10000',
    description: 'Sanitizer-enforced cap on rows returned by generated SELECT statements.',
    expect:
      'LLM SQL that would return more rows is rewritten or rejected before execution — protects the API and browsers from huge payloads.',
  },
  {
    name: 'MAX_JOINS',
    type: 'integer',
    default: '10',
    description: 'AST validator limit on JOIN count in a single query.',
    expect: 'Absurd join chains fail validation with a clear error instead of running expensive SQL.',
  },
  {
    name: 'QUERY_TIMEOUT_SECONDS',
    type: 'integer',
    default: '30',
    description: 'Database statement timeout for executed SQL.',
    expect:
      'Long-running analytics queries cancel with a timeout error; the HTTP request does not hang indefinitely.',
  },
  {
    name: 'QUERY_ROW_CAP',
    type: 'integer',
    default: '10000',
    description: 'Executor-level row cap after sanitization (defense in depth).',
    expect: 'Even if sanitization misconfigured, the executor stops pulling rows beyond this cap.',
  },
];

export const vectorConfig: ConfigRow[] = [
  {
    name: 'VECTOR_STORE',
    type: 'string',
    default: 'none',
    description:
      'Vector backend for optional RAG: `none` (default), `chroma`, or a custom class via `VECTOR_STORE_CLASS`.',
    expect:
      'With `none`, `/v1/vector/*` and RAG enhancement are inactive. With `chroma`, you must build the API image with the Chroma extra and run reindex after catalog changes.',
  },
  {
    name: 'CHROMA_PERSIST_PATH',
    type: 'path',
    default: '/app/data/chroma',
    description: 'On-disk directory for Chroma persistence inside the container.',
    expect:
      'Mount a volume at this path in production so reindex survives restarts; empty path after wipe requires `POST /v1/vector/reindex`.',
  },
  {
    name: 'EMBEDDING_MODEL',
    type: 'string',
    default: 'text-embedding-3-small',
    description: 'LiteLLM embedding model id used when indexing and querying vectors.',
    expect:
      'Changing the model invalidates prior vectors — reindex before expecting RAG hits. Default `text-embedding-3-small` uses OpenAI; set `OPENAI_API_KEY` or `LLM_API_KEY` (or a key matching your `EMBEDDING_MODEL` provider). Startup logs warn when `VECTOR_STORE=chroma` but no embedding credentials are configured.',
  },
  {
    name: 'RAG_TOP_K',
    type: 'integer',
    default: '5',
    description: 'Number of chunks merged into chat enhancement context per turn.',
    expect:
      'Higher values add more document snippets to the prompt (more latency and tokens); lower values may miss relevant passages.',
  },
];

export const corsConfig: ConfigRow[] = [
  {
    name: 'CORS_ORIGINS',
    type: 'JSON array',
    default: 'localhost:3000,3001,5173',
    description:
      'Browser origins allowed to call the API with credentials from your docs site, dashboard, or custom frontend.',
    expect:
      'Misconfigured origins show browser CORS errors in the network tab — the API itself may still work from curl or server-side SDKs.',
  },
  {
    name: 'API_PORT',
    type: 'integer',
    default: '8000',
    description: 'Host port published for the API service in Compose (not read by Python Settings).',
    expect: 'SDK `baseUrl` and health checks target `http://localhost:8000` in local stacks.',
  },
];
