# Seal — setup notes

Quick reference for SDK install, auth, and local services. For full contributor workflow see **[CONTRIBUTORS.md](CONTRIBUTORS.md)**; for production Docker see **[DEPLOYMENT.md](DEPLOYMENT.md)**; for all `docs/` markdown see **[docs/README.md](docs/README.md)**.

## Packages

| Artifact | Name |
|----------|------|
| PyPI | `seal` |
| npm | `seal` |
| Docker | `seal/api` |
| Postgres (default) | `seal` |

```bash
pip install seal
npm install seal
docker pull seal/api:latest
```

## SDK usage

Python:

```python
from seal import Seal

with Seal("http://localhost:8000", api_key="your-secret-here") as client:
    result = client.query("Revenue by month")
```

TypeScript:

```ts
import { Seal } from "seal";

const client = new Seal({
  baseUrl: "http://localhost:8000",
  apiKey: "your-secret-here",
});
```

`ConnectionError` is an alias for `SealConnectionError`.

## API authentication

Seal uses a **shared API key** (not OAuth or JWT). When `SEAL_API_KEY` is set, all `/v1/*` routes require the `X-API-Key` header. `GET /health` stays public for probes.

| Variable | Purpose |
|----------|---------|
| `SEAL_API_KEY` | Shared secret; whitespace-only values are ignored (auth off). |
| `SEAL_AUTH_REQUIRED` | If `true`, the API **refuses to start** without a real key. Placeholders are always rejected when this is `true`, even if `SEAL_DEV_MODE=true`. |
| `SEAL_DISABLE_DOCS` | If `true`, hides `/docs`, `/redoc`, `/openapi.json` (defaults to `SEAL_AUTH_REQUIRED` when unset). |
| `SEAL_DEV_MODE` | If `true` and `SEAL_AUTH_REQUIRED=false`, allows placeholder keys for local dev only. Must be `false` in production. |

**Production (recommended):**

```bash
SEAL_API_KEY=$(openssl rand -hex 32)
SEAL_AUTH_REQUIRED=true
SEAL_DEV_MODE=false
SEAL_DISABLE_DOCS=true
```

**Local dev (repo `make up`):** copy `.env.example` → `.env` (placeholder key + `SEAL_DEV_MODE=true`). Root `docker-compose.yml` requires `SEAL_API_KEY` in `.env` but does not ship a default secret.

**Production (image-only compose):** `docker-compose.example.yml` requires a real `SEAL_API_KEY` in `.env`, sets `SEAL_AUTH_REQUIRED=true`, `SEAL_DEV_MODE=false`, and `SEAL_DISABLE_DOCS=true` by default.

**Clients:** SDKs accept `api_key` / `apiKey` and send `X-API-Key`. Raw HTTP:

```bash
curl -H "X-API-Key: $SEAL_API_KEY" http://localhost:8000/v1/schema
```

**Security details:**

- Comparison uses `secrets.compare_digest` (timing-safe).
- Wrong keys return `401` with a generic message (no leak of expected value).
- Do not embed production keys in frontend bundles; call Seal from your backend.
- End users should authenticate to **your** app; your server calls Seal (BFF pattern). See [docs/embedding.md](docs/embedding.md).
- Use a reverse proxy for rate limits on public deployments.

Full guides: docs site **Authentication** (`/docs/authentication`) · **Embedding Seal** (`/docs/embedding`).

## Data catalog & chat

On startup, Seal can auto-sync `config/catalog.yaml` from introspected schema (`CATALOG_AUTO_SYNC=true`). Edit `table_description` / `view_description` in that file to improve NL query and chat answers.

- `GET /v1/catalog` — read catalog JSON
- `POST /v1/catalog/sync` — force re-sync
- `PATCH /v1/catalog/descriptions` — table/view description overrides
- `POST /v1/chat` — schema-grounded Q&A (`include_charts`, `stream`, `enhancement`)
- `GET` / `PATCH /v1/workspace/settings` — workspace settings (see [docs/workspace-api.md](docs/workspace-api.md))
- `POST /v1/vector/reindex` — rebuild vector index when `VECTOR_STORE` is enabled

**Guardrails** (see [docs/guardrails.md](docs/guardrails.md)): `GUARDRAILS_ENABLED`, `GUARDRAILS_FAIL_CLOSED`, `MAX_QUERY_CHARS`, `MAX_CHAT_MESSAGE_CHARS`, `MAX_CHAT_HISTORY_CHARS`. Out-of-scope chat returns HTTP 200 with a refusal and `metadata.suggested_queries`; out-of-scope query returns HTTP 400 with structured `detail` (`query_out_of_scope`, `reason`, `suggested_queries`). Oversized bodies may return **422** from request validation before guardrails run.

**Local UIs**: docs `apps/docs` (port 3000), dashboard `apps/web` (port 3001). Run `make up` for API, then `cd apps/docs && pnpm dev` and `cd apps/web && pnpm dev` in separate terminals.

Optional vector RAG: `VECTOR_STORE=chroma` with `seal-core[chroma]` installed. Default is `VECTOR_STORE=none`.

**Multiple databases (optional):** copy `config/databases.example.yaml` → `config/databases.yaml`, restart API, pass `database_id` on query/chat/schema. [docs/multi-database.md](docs/multi-database.md).

```bash
make sync-catalog   # CLI sync without restarting API
```

### SDK examples

```python
from seal import Seal

with Seal("http://localhost:8000", api_key="your-secret") as client:
    client.catalog()
    client.chat("Revenue last quarter?", include_charts=True)
```

```typescript
import { Seal } from "seal";

const client = new Seal({ baseUrl: "http://localhost:8000", apiKey: "your-secret" });
await client.chat("Revenue last quarter?", { includeCharts: true });
```

**Contributor docs:** index at [docs/README.md](docs/README.md). User-facing: docs site `http://localhost:3000` (`/docs/embedding`, `/docs/integration-guide`, `/docs/how-it-works`, `/docs/execution-metadata`, `/docs/multi-database`, `/docs/guardrails`); dashboard `http://localhost:3001` ([apps/web/README.md](apps/web/README.md)).

**API schema changes:** edit `apps/api/app/schemas.py`, then from repo root run `make openapi-ts` and commit the OpenAPI spec, docs copies, and `sdks/typescript/src/generated/openapi.ts`. Verify with `make verify-openapi-sync` (also run in CI).

**Tests:** CI runs unit tests and live E2E on every PR. Locally: `make check` (unit, OpenAPI sync, metadata contract checks, docs/dashboard builds — mirrors most of CI) and `make check-e2e` (requires `make up`). Pre-commit hooks do not run pytest.

**Local planner evals (not in CI):** After `make up && make seed`, run `make eval-planner` or `make eval`. See [docs/local-evals.md](docs/local-evals.md). Unit tests: `uv run pytest evals/tests/test_runner.py -v`.

## Docker database

Default compose uses database name `seal`. If you change `POSTGRES_DB`, update `DATABASE_URL` to match.
