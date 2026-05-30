# Seal — setup notes

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

`ConnectionError` remains available as a deprecated alias for `SealConnectionError`.

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
- End users should authenticate to **your** app; your server calls Seal (BFF pattern).
- Use a reverse proxy for rate limits on public deployments.

**Local dev:** copy `.env.example` → `.env` (includes a dev-only key). `docker-compose.yml` does not default a production key.

Full guide on the docs site: **Authentication** (`/docs/authentication`).

## Docker database

Default compose uses database name `seal`. If you change `POSTGRES_DB`, update `DATABASE_URL` to match.
