# Seal TypeScript SDK

**Docs:** [docs/README.md](../../docs/README.md) · embedding [docs/embedding.md](../../docs/embedding.md) · multi-database [docs/multi-database.md](../../docs/multi-database.md)

## Type generation (OpenAPI)

API request/response types are **not** hand-maintained. They are generated from the FastAPI OpenAPI spec (Pydantic v2 models in `apps/api/app/schemas.py`):

1. `make openapi` — writes `apps/api/openapi.json`
2. `make openapi-ts` — runs [openapi-typescript](https://github.com/openapi-ts/openapi-typescript) → `src/generated/openapi.ts`
3. `src/types.ts` re-exports `components['schemas'][…]` for the public SDK surface

After changing API models, run from the repo root:

```bash
make openapi-ts
cd sdks/typescript && pnpm run build
```

`scripts/generate_openapi.py` injects Pydantic models that appear only in manual route `responses` (for example `ChatStreamMeta` for SSE and `QueryOutOfScopeErrorResponse` for guardrails 400) so they land in `components/schemas`.

CI enforces this via `make verify-openapi-sync` (committed `src/generated/openapi.ts`; `src/vendor/` is gitignored and copied on `prebuild`).

Public types include `QueryOutOfScopeDetail`, `QueryOutOfScopeErrorResponse`, and `QueryOutOfScopeError` for structured guardrails failures on `client.query()`.

`ReasoningMetadata` / `ReasoningInfo` describe `metadata.reasoning` on query and chat responses (`clarification_required`, `clarifying_questions`, `analysis_followups`, `research_notes`, `inferred_context`). Query may also return top-level `message` when clarification is required.

## Runtime metadata (SSE)

Wire types (`ChatStreamMeta`, `ChatMetadata`, `QueryMetadata`) come from OpenAPI. **Runtime** checks for streaming use vendored copies of `shared/stream-meta.ts` and `shared/chat-sse-events.ts` (`mapChatSseEvent` → `meta` | `meta_error` | `delta` | `done`), aligned with server `validate_metadata.py`. See [docs/chat-metadata.md](../../docs/chat-metadata.md).

## Usage

```typescript
import { Seal } from 'seal';

const client = new Seal({ baseUrl: 'http://localhost:8000', apiKey: process.env.SEAL_API_KEY });

const result = await client.query('Monthly revenue by region');
console.log(result.metadata?.database_id, result.sql, result.message);

if (result.metadata?.reasoning?.clarification_required) {
  console.log(result.metadata.reasoning.clarifying_questions);
}

for await (const event of client.chatStream('Summarize last quarter', { includeCharts: true })) {
  if (event.type === 'meta') console.log(event.data.sql);
  else if (event.type === 'meta_error') console.warn('Invalid seal.meta', event.data);
  else if (event.type === 'delta') process.stdout.write(event.content);
}
```

### Guardrails errors

Out-of-scope **query** calls throw `QueryOutOfScopeError` with `reason` and `suggestedQueries` parsed from the API body (`detail.detail === 'query_out_of_scope'`). Out-of-scope **chat** returns HTTP 200; read `response.metadata.suggested_queries` or `event.data.suggested_queries` on the first `seal.meta` event when streaming.

When reasoning is enabled, chat streaming may emit a **second** `seal.meta` after answer tokens finish (updated `reasoning` with LLM follow-ups). Treat each `meta` event as an update to the same turn.

### Multiple databases

```typescript
const result = await client.query('Total orders', 'default');
const schema = await client.schema({ databaseId: 'analytics' });
await client.chat('What tables exist?', { databaseId: 'analytics' });
```
