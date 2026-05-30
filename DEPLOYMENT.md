# Deployment Guide (Self-Hosting)

Seal is Docker-first: run the `seal/api` image with Postgres (and optionally Ollama or a cloud LLM) for NL query, **chat Q&A**, and chart generation.

## Architecture

| Service | Role |
| ------- | ---- |
| **API** | FastAPI — `/v1/query`, `/v1/chat`, `/v1/catalog`, `/v1/schema` |
| **Postgres** | TimescaleDB analytics DB (bundled in compose) |
| **Ollama** | Local LLM (optional; `OLLAMA_PROFILE=disabled` for cloud) |

On startup the API can **auto-sync** `config/catalog.yaml` from introspected schema and build an optional **vector index** when `VECTOR_STORE=chroma`.

## Prerequisites

- Docker and Docker Compose
- Ports `8000`, `5432`, and (for Ollama) `11434` available
- For production: generate `SEAL_API_KEY` and set auth flags (see below)

## Quick Start (Local Development)

```bash
cp .env.example .env
make up
make seed
curl http://localhost:8000/health
```

With API key from `.env`:

```bash
curl -H "X-API-Key: $SEAL_API_KEY" http://localhost:8000/v1/catalog

curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SEAL_API_KEY" \
  -d '{"message":"What tables exist?"}'
```

For **cloud LLM** (Gemini, OpenAI, Anthropic), set in `.env`:

```bash
OLLAMA_PROFILE=disabled
LLM_MODEL=gemini/gemini-1.5-flash
LLM_API_KEY=your-key-here
```

Then `make up` (Ollama container is not started).

## Production Deployment

`make docker-build` produces the `prod` image (non-root user).

Use the published compose example (also at `apps/web/public/compose/docker-compose.example.yml` on the docs site):

1. Download `docker-compose.example.yml` and `seed.sql`.
2. Create `.env` with `SEAL_API_KEY`, `SEAL_AUTH_REQUIRED=true`, `SEAL_DEV_MODE=false`, `SEAL_DISABLE_DOCS=true`.
3. Mount a host directory for the data catalog, e.g. `./config:/app/config`.

### Environment Variables

#### Core

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Postgres/asyncpg connection string | `postgresql+asyncpg://…` |
| `SEAL_API_KEY` | Shared secret for `X-API-Key` on `/v1/*` | — |
| `SEAL_AUTH_REQUIRED` | Fail startup without a real key | `false` (dev), `true` (prod example) |
| `SEAL_DEV_MODE` | Allow placeholder keys when auth not required | `true` (dev) |
| `SEAL_DISABLE_DOCS` | Hide `/docs` and `/openapi.json` | follows auth in prod |
| `CORS_ORIGINS` | JSON array of browser origins | `["http://localhost:3000"]` |
| `MAX_ROWS` | Row cap for generated SQL | `10000` |
| `QUERY_TIMEOUT_SECONDS` | SQL execution timeout | `30` |

#### LLM

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_PROFILE` | `default` = Ollama; `disabled` = cloud | `default` |
| `LLM_MODEL` | LiteLLM model id | `ollama/llama3.2:1b` |
| `LLM_BASE_URL` | Ollama URL (ignored when profile disabled) | `http://ollama:11434` |
| `LLM_API_KEY` | Cloud API key (or provider-specific vars) | — |

#### Data catalog & chat

| Variable | Description | Default |
|----------|-------------|---------|
| `DATA_CATALOG_PATH` | Path to auto-generated catalog YAML | `config/catalog.yaml` |
| `CATALOG_AUTO_SYNC` | Sync catalog from DB schema on startup | `true` |
| `CATALOG_PRUNE_REMOVED` | Drop YAML entries for removed tables | `false` |
| `CHAT_ENHANCEMENT_ENABLED` | Prompt enhancer chain on `/v1/chat` | `true` |
| `VECTOR_STORE` | `none`, `chroma`, or custom via `VECTOR_STORE_CLASS` | `none` |
| `VECTOR_STORE_CLASS` | Dotted path to custom vector store | — |
| `RAG_DOCUMENTS_PATH` | Extra files to index for RAG | — |
| `RAG_TOP_K` | Vector retrieval top-K | `5` |

The API logs **warnings** at startup for common misconfigurations (e.g. cloud model without `OLLAMA_PROFILE=disabled`).

### Volumes (recommended)

```yaml
services:
  api:
    volumes:
      - ./config:/app/config
```

Edit `config/catalog.yaml` after sync to add `table_description` / `view_description` for better NL accuracy.

### Optional: Chroma vector RAG

Install `seal-core[chroma]` in the image (Linux builds) or use a custom store:

```bash
VECTOR_STORE=chroma
```

Persist Chroma data with an additional volume if using the reference implementation.

### Standalone `docker run` (cloud)

```bash
docker run -d -p 8000:8000 \
  -e OLLAMA_PROFILE=disabled \
  -e DATABASE_URL="postgresql+asyncpg://user:pass@dbhost/mydb" \
  -e LLM_MODEL="gemini/gemini-1.5-flash" \
  -e LLM_API_KEY="your-key" \
  -e SEAL_API_KEY="$(openssl rand -hex 32)" \
  -e SEAL_AUTH_REQUIRED=true \
  -e CHAT_ENHANCEMENT_ENABLED=true \
  -v "$(pwd)/config:/app/config" \
  seal/api:latest
```

## Agent frameworks

Ship HTTP tools without embedding Seal in-process:

- Manifest: `config/seal-tools.openai.json` (`seal_get_schema`, `seal_get_catalog`, `seal_query`, `seal_chat`)
- Docs: [docs/integrations/agent-frameworks.md](docs/integrations/agent-frameworks.md)

When the external agent already has RAG, set `VECTOR_STORE=none` and pass `enhancement: false` on chat requests.

## Health Checks

The production image health-checks `GET /health`. Use the same endpoint in your load balancer. Authenticated routes require `X-API-Key`.

## Docs site (optional)

Deploy `apps/web` to Vercel for documentation and demo UI — see [apps/web/DEPLOYMENT.md](apps/web/DEPLOYMENT.md). The demo can call a live API when `baseUrl` and API key are configured on `/demo`.
