# Deployment Guide (Self-Hosting)

Seal is Docker-first: run the `seal/api` image with Postgres (and optionally Ollama or a cloud LLM) for NL query, **chat Q&A**, and chart generation.

**Related guides:** [docs/embedding.md](docs/embedding.md) (BFF pattern, boundaries) · [docs/multi-database.md](docs/multi-database.md) (`database_id`) · [CONTRIBUTORS.md](CONTRIBUTORS.md) (dev setup) · [docs/README.md](docs/README.md) (full doc index) · [AWS deployment](#aws-deployment) (ECS Fargate, Lambda)

## Architecture

| Service       | Role                                                                                               |
| ------------- | -------------------------------------------------------------------------------------------------- |
| **API**       | FastAPI — `/v1/query`, `/v1/chat`, `/v1/catalog`, `/v1/schema`, `/v1/databases`, workspace, vector |
| **Docs**      | `apps/docs` (port 3000) — guides, `/docs/embedding`, fixture `/demo`                               |
| **Dashboard** | `apps/web` (port 3001) — live API console (Query, Chat, Schema, Catalog, Settings, Vector)         |
| **Postgres**  | TimescaleDB analytics DB (bundled in compose)                                                      |
| **Ollama**    | Local LLM (optional; `OLLAMA_PROFILE=disabled` for cloud)                                          |

On startup the API can **auto-sync** `config/catalog.yaml` from introspected schema (default database) and build an optional **vector index** when `VECTOR_STORE=chroma`.

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

# List registered database ids (when multi-DB is configured)
curl -H "X-API-Key: $SEAL_API_KEY" http://localhost:8000/v1/databases

curl -s -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SEAL_API_KEY" \
  -d '{"query":"Count orders by month","database_id":"default"}'

curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SEAL_API_KEY" \
  -d '{"message":"What tables exist?","database_id":"default"}'
```

Responses include **`metadata.database_id`**, execution stats when SQL runs (`row_count`, `execution_time_ms`, `repair_attempts`, `used_sql`), and on guardrails refusal **`metadata.suggested_queries`** (chat) or HTTP 400 with nested **`detail`** on query (fields at `detail.detail`, `detail.reason`, `detail.suggested_queries`). See [docs/chat-metadata.md](docs/chat-metadata.md) and [docs/guardrails.md](docs/guardrails.md).

For **cloud LLM** (Gemini, OpenAI, Anthropic), set in `.env`:

```bash
OLLAMA_PROFILE=disabled
LLM_MODEL=gemini/gemini-1.5-flash
LLM_API_KEY=your-key-here
```

Then `make up` (Ollama container is not started).

## Production Deployment

`make docker-build` produces the `prod` image (non-root user).

Use the published compose example (also at `apps/docs/public/compose/docker-compose.example.yml` on the docs site):

1. Download `docker-compose.example.yml` and `seed.sql`.
2. Create `.env` with `SEAL_API_KEY`, `SEAL_AUTH_REQUIRED=true`, `SEAL_DEV_MODE=false`, `SEAL_DISABLE_DOCS=true`.
3. Mount a host directory for config, e.g. `./config:/app/config` (catalog YAML, optional `databases.yaml`, workspace fallback).
4. Apply workspace schema once: `psql … < scripts/migrate_app.sql` (creates `seal_app.workspace_kv` for settings and catalog description overrides).
5. Optional: copy `config/databases.example.yaml` → `config/databases.yaml` for extra `database_id` backends.

### Environment Variables

#### Core

| Variable                | Description                                                     | Default                                             |
| ----------------------- | --------------------------------------------------------------- | --------------------------------------------------- |
| `DATABASE_URL`          | Primary DB; always registered as `database_id` **default**      | `postgresql+asyncpg://…`                            |
| `SEAL_DATABASES_PATH`   | Optional YAML for additional ids (e.g. `config/databases.yaml`) | `config/databases.yaml`                             |
| `SEAL_DATABASES`        | Optional JSON env map of id → URL (Docker-friendly)             | —                                                   |
| `SEAL_API_KEY`          | Shared secret for `X-API-Key` on `/v1/*`                        | —                                                   |
| `SEAL_AUTH_REQUIRED`    | Fail startup without a real key                                 | `false` (dev), `true` (prod example)                |
| `SEAL_DEV_MODE`         | Allow placeholder keys when auth not required                   | `true` (dev)                                        |
| `SEAL_DISABLE_DOCS`     | Hide `/docs` and `/openapi.json`                                | follows auth in prod                                |
| `CORS_ORIGINS`          | JSON array of browser origins                                   | `["http://localhost:3000","http://localhost:3001"]` |
| `MAX_ROWS`              | Row cap for generated SQL                                       | `10000`                                             |
| `QUERY_TIMEOUT_SECONDS` | SQL execution timeout                                           | `30`                                                |

#### LLM

| Variable         | Description                                | Default               |
| ---------------- | ------------------------------------------ | --------------------- |
| `OLLAMA_PROFILE` | `default` = Ollama; `disabled` = cloud     | `default`             |
| `LLM_MODEL`      | LiteLLM model id                           | `ollama/llama3.2:1b`  |
| `LLM_BASE_URL`   | Ollama URL (ignored when profile disabled) | `http://ollama:11434` |
| `LLM_API_KEY`    | Cloud API key (or provider-specific vars)  | —                     |

#### Data catalog & chat

| Variable                        | Description                                          | Default               |
| ------------------------------- | ---------------------------------------------------- | --------------------- |
| `DATA_CATALOG_PATH`             | Path to auto-generated catalog YAML                  | `config/catalog.yaml` |
| `CATALOG_AUTO_SYNC`             | Sync catalog from DB schema on startup               | `true`                |
| `CATALOG_PRUNE_REMOVED`         | Drop YAML entries for removed tables                 | `false`               |
| `CHAT_ENHANCEMENT_ENABLED`      | Prompt enhancer chain on `/v1/chat`                  | `true`                |
| `CHAT_SESSION_TTL_SECONDS`      | In-memory chat session TTL                           | `3600`                |
| `CHAT_MAX_HISTORY_MESSAGES`     | Max messages stored per session                      | `20`                  |
| `CHAT_SUMMARIZE_AFTER_MESSAGES` | Summarize when history exceeds this count            | `12`                  |
| `CHAT_RECENT_MESSAGES`          | Recent messages kept verbatim at answer stage        | `6`                   |
| `CHAT_ANSWER_PREVIEW_ROWS`      | Result rows sent to the LLM as grounding facts       | `20`                  |
| `CHAT_MAX_CONTEXT_TABLES`       | Max tables in focused schema/catalog context         | `8`                   |
| `VECTOR_STORE`                  | `none`, `chroma`, or custom via `VECTOR_STORE_CLASS` | `none`                |
| `VECTOR_STORE_CLASS`            | Dotted path to custom vector store                   | —                     |
| `RAG_DOCUMENTS_PATH`            | Extra files to index for RAG                         | —                     |
| `RAG_TOP_K`                     | Vector retrieval top-K                               | `5`                   |

#### Guardrails

| Variable                 | Description                      | Default |
| ------------------------ | -------------------------------- | ------- |
| `GUARDRAILS_ENABLED`     | Scope gate on query/chat         | `true`  |
| `GUARDRAILS_FAIL_CLOSED` | Classifier errors → out-of-scope | `true`  |
| `MAX_QUERY_CHARS`        | `/v1/query` input limit          | `4000`  |
| `MAX_CHAT_MESSAGE_CHARS` | Single chat message limit        | `8000`  |
| `MAX_CHAT_HISTORY_CHARS` | History override limit           | `32000` |

See [docs/guardrails.md](docs/guardrails.md). Out-of-scope **query** → HTTP 400 with a nested JSON body:

```json
{
  "detail": {
    "detail": "query_out_of_scope",
    "reason": "off-topic pattern",
    "suggested_queries": [
      "Show order count by month",
      "What tables are available?"
    ]
  }
}
```

Out-of-scope **chat** → HTTP 200 refusal with `metadata.suggested_queries`. Hot-reload on save when `SEAL_DEV_MODE=true`; in production use `POST /v1/workspace/settings/apply` (dashboard **Apply to API**).

#### Multi-database (optional)

Copy `config/databases.example.yaml` → `config/databases.yaml` and mount `./config:/app/config`. Clients pass `database_id` on `/v1/query`, `/v1/chat`, and `GET /v1/schema` — never raw connection strings. Catalog, semantic layer, and vector index remain on **default** only. Details: [docs/multi-database.md](docs/multi-database.md).

#### Workspace

Apply `scripts/migrate_app.sql` to create `seal_app.workspace_kv`. Routes: [docs/workspace-api.md](docs/workspace-api.md).

The API logs **warnings** at startup for common misconfigurations (e.g. cloud model without `OLLAMA_PROFILE=disabled`).

### Volumes (recommended)

```yaml
services:
  api:
    volumes:
      - ./config:/app/config
```

Edit `config/catalog.yaml` after sync to add `table_description` / `view_description` for better NL accuracy.

Example `config/databases.yaml` (mount with `./config:/app/config`):

```yaml
databases:
  analytics:
    url: duckdb:///data/analytics.duckdb
```

Clients pass `"database_id": "analytics"` on `/v1/query`, `/v1/chat`, and `GET /v1/schema?database_id=analytics`. Unknown ids → HTTP **404** `unknown_database_id`.

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

## Embedding in your product

Seal is an **internal capability layer**, not a user-facing app.

1. Set `SEAL_API_KEY` and call Seal from **your backend** only (`X-API-Key`).
2. End users authenticate to your product (JWT, session, SSO); your server forwards NL requests to Seal.
3. Put a reverse proxy or API gateway in front for rate limits on public deployments.
4. Understand three boundaries: **guardrails** (scope) → **SQLGlot** (zero-trust SQL) → **enhancement/RAG** (chat only).

Full guide: [docs/embedding.md](docs/embedding.md) · docs site `/docs/embedding` · auth: `/docs/authentication`.

## Agent frameworks

Ship HTTP tools without embedding Seal in-process:

- Manifest: `config/seal-tools.openai.json` (`seal_get_schema`, `seal_get_catalog`, `seal_query`, `seal_chat`)
- Docs: [docs/integrations/agent-frameworks.md](docs/integrations/agent-frameworks.md)

When the external agent already has RAG, set `VECTOR_STORE=none` and pass `enhancement: false` on chat requests. Tools accept optional `database_id` when multiple backends are registered.

## API surface (integrators)

| Endpoint                               | Notes                                                                                                           |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `POST /v1/query`                       | Stateless NL → SQL + chart; optional `database_id`; OOS → **400** + `suggested_queries`                         |
| `POST /v1/chat`                        | Sessions, streaming, optional charts; `database_id` on every turn; OOS → **200** + `metadata.suggested_queries` |
| `GET /v1/schema`                       | `?database_id=` query param                                                                                     |
| `GET /v1/databases`                    | List registered ids                                                                                             |
| `GET /v1/catalog`                      | Global catalog (from **default** introspection)                                                                 |
| `GET` / `PATCH /v1/workspace/settings` | Guardrails, chat, vector settings                                                                               |
| `POST /v1/vector/reindex`              | Rebuild index (default DB schema)                                                                               |

OpenAPI: `/openapi.json` when `SEAL_DISABLE_DOCS=false`. SDKs: PyPI/npm package `seal`.

## Health Checks

The production image health-checks `GET /health`. Use the same endpoint in your load balancer. Authenticated routes require `X-API-Key`.

## Frontends (optional)

| App         | Port | Deploy                                                          |
| ----------- | ---- | --------------------------------------------------------------- |
| `apps/docs` | 3000 | Vercel — see [apps/docs/DEPLOYMENT.md](apps/docs/DEPLOYMENT.md) |
| `apps/web`  | 3001 | Same host or separate origin; requires `CORS_ORIGINS`           |

The docs `/demo` route uses static fixtures; the dashboard always calls a live API (`baseUrl` + `X-API-Key` + **Database** dropdown for `database_id`).

## Documentation index

| Audience                 | Location                                                                                 |
| ------------------------ | ---------------------------------------------------------------------------------------- |
| Contributors             | [CONTRIBUTORS.md](CONTRIBUTORS.md), [docs/README.md](docs/README.md)                     |
| Releases                 | [RELEASING.md](RELEASING.md)                                                             |
| Quick SDK/auth reference | [SETUP.md](SETUP.md)                                                                     |
| Integrators (embedding)  | [docs/embedding.md](docs/embedding.md) → `/docs/embedding`                               |
| Multi-database           | [docs/multi-database.md](docs/multi-database.md) → `/docs/multi-database`                |
| Guardrails & metadata    | [docs/guardrails.md](docs/guardrails.md), [docs/chat-metadata.md](docs/chat-metadata.md) |
| End users (hosted docs)  | `apps/docs` → `/docs/integration-guide`, `/docs/self-hosting`, `/docs/authentication`    |
| Vercel (docs site only)  | [apps/docs/DEPLOYMENT.md](apps/docs/DEPLOYMENT.md)                                       |
| AWS (ECS / Lambda)       | [AWS deployment](#aws-deployment) (this guide)                                           |

## AWS deployment

Seal ships as the **`seal/api`** Docker image (`apps/api/Dockerfile`, `prod` target). Heavy ML runs in **cloud LLM APIs** (LiteLLM); AWS compute is mostly I/O-bound: HTTP, SQLGlot validation, Postgres execution, optional Chroma RAG, and Vega-Lite chart specs.

Use the same environment variables as [Production Deployment](#production-deployment). On AWS you typically set `OLLAMA_PROFILE=disabled`, point `DATABASE_URL` at **RDS/Aurora Postgres**, store `SEAL_API_KEY` and `LLM_API_KEY` in **Secrets Manager**, and mount or sync `./config` (catalog YAML, optional `databases.yaml`) via **EFS** or an init container.

```mermaid
flowchart LR
  clients[Clients / BFF] --> alb[ALB or Lambda URL]
  alb --> api[seal/api]
  api --> rds[(RDS Postgres)]
  api --> llm[Cloud LLM APIs]
  api -. optional .-> efs[EFS config volume]
```

### ECS Fargate (recommended for production)

**Best for:** Steady or high-throughput traffic, long-lived DB pools, multi-turn **chat sessions** (in-memory `SessionStore` per task), and **SSE** streaming without Lambda’s 15-minute cap.

| Component | Suggestion |
| --------- | ---------- |
| **Compute** | ECS service on Fargate; task definition uses `seal/api:latest` (or your ECR mirror). |
| **Load balancer** | ALB → target group; health check `GET /health` on port **8000**. |
| **Database** | RDS/Aurora Postgres; run `scripts/migrate_app.sql` once for `seal_app.workspace_kv`. |
| **Secrets** | `SEAL_API_KEY`, `LLM_API_KEY`, `DATABASE_URL` from Secrets Manager or SSM. |
| **Config** | EFS mount at `/app/config` (`DATA_CATALOG_PATH`, catalog overrides). |
| **LLM** | `OLLAMA_PROFILE=disabled`, `LLM_MODEL=gemini/...` or `openai/...` (no Ollama sidecar). |
| **Auth** | `SEAL_AUTH_REQUIRED=true`, `SEAL_DEV_MODE=false`, `SEAL_DISABLE_DOCS=true`. |
| **Scaling** | Target tracking on CPU/latency; new tasks often take **1–3 minutes** (image pull + boot). |

**Multi-task chat:** Chat history is **in-process** unless you change storage. For more than one API task, use **sticky sessions** on the ALB or treat chat as best-effort per instance until you add external session storage.

**Example task env (illustrative):**

```bash
OLLAMA_PROFILE=disabled
LLM_MODEL=openai/gpt-4o-mini
DATABASE_URL=postgresql+asyncpg://user:pass@mydb.xxxx.us-east-1.rds.amazonaws.com:5432/seal
SEAL_API_KEY=<from-secrets-manager>
SEAL_AUTH_REQUIRED=true
SEAL_DEV_MODE=false
SEAL_DISABLE_DOCS=true
CORS_ORIGINS=["https://app.example.com"]
CHAT_ENHANCEMENT_ENABLED=true
VECTOR_STORE=none
```

Push the image to ECR with `docker tag seal/api:latest <account>.dkr.ecr.<region>.amazonaws.com/seal/api:latest` after `make docker-build`.

### Lambda (container image, scale-to-zero)

**Best for:** Internal tools with **spiky or rare** traffic where idle cost should be **$0**. Most request time is spent waiting on **external LLM APIs**, which fits Lambda’s I/O profile.

**Seal-specific caveats:**

| Topic | Lambda behavior |
| ----- | ---------------- |
| **Idle cost** | Scales to zero between invocations. |
| **Cold start** | Often faster than ECS task launch (Firecracker + block lazy-load of image layers). |
| **Max duration** | **15 minutes** per invocation — enough for most queries; watch repair loops × LLM latency. |
| **Chat sessions** | In-memory sessions do **not** survive cold starts or concurrent executions; prefer **stateless** `/v1/query` or accept session loss unless you add shared session storage. |
| **DB connections** | One concurrent invocation ≈ one pool; use **RDS Proxy** (or PgBouncer) to avoid exhausting Postgres `max_connections`. |
| **Streaming** | Prefer **Lambda Function URLs** (up to 15 min, response streaming) over API Gateway REST (29 s integration timeout). |
| **RAG / Chroma** | Default `VECTOR_STORE=none` on Lambda; if using Chroma, cache under `/tmp` (up to 10 GB ephemeral) or use an external vector service. |

### ECS Fargate vs Lambda

| | **Lambda (container)** | **ECS Fargate** |
| --- | --- | --- |
| **Idle cost** | $0 (scale to zero) | Baseline per task (~$11+/mo minimum footprint) |
| **Scale-out speed** | Milliseconds–seconds (cold/warm starts) | Minutes (new task provisioning) |
| **Max request time** | 15 minutes | Unlimited (ALB idle timeout configurable) |
| **DB connection pools** | Short-lived; use **RDS Proxy** | Long-lived pools per task |
| **Chat / SSE** | Sessions ephemeral; use Function URLs for stream | Natural fit for sticky sessions + long streams |
| **Ops model** | Per-invocation billing | Always-on service |

### One image: ECS and Lambda (Lambda Web Adapter)

To avoid two codebases, teams can add the [AWS Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter) to the **same** `seal/api` image. On ECS the adapter is inert; on Lambda it forwards events to Uvicorn over HTTP.

The stock image listens on port **8000** (`apps/api/Dockerfile`). For Lambda, set `PORT` (adapter default **8080**) and point the process at that port — e.g. extend the **prod** stage:

```dockerfile
# Optional — only if you deploy the same image to Lambda
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter
ENV PORT=8080
CMD ["uv", "run", "uvicorn", "app.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8080"]
```

Configure the Lambda function with **Function URL** or ALB integration, container image from ECR, and the same secrets/env as ECS. Health checks in ECS still use `GET /health` on the task port.

### AWS tuning checklist

1. **RDS Proxy** in front of Postgres when using Lambda or many Fargate tasks.
2. **Lambda Function URLs** (or HTTP API with 15 min timeout) for `/v1/query` and `/v1/chat` when LLM + repair can exceed **29 s**.
3. **`QUERY_TIMEOUT_SECONDS`** — align with ALB/Lambda timeout and expected SQL runtime.
4. **`CORS_ORIGINS`** — list your dashboard/docs origins if browsers call the API directly.
5. **Workspace** — `migrate_app.sql` on RDS; production settings via `POST /v1/workspace/settings/apply` (not dev hot-reload).
6. **Gateway** — WAF or API Gateway in front of public endpoints; rate-limit `POST /v1/query` and failed `X-API-Key` (see [docs/embedding.md](docs/embedding.md)).
7. **Chroma** — if `VECTOR_STORE=chroma`, persist index data on EFS (ECS) or `/tmp` warm cache (Lambda); image may need `SEAL_EXTRA=chroma` at build time.
8. **Observability** — CloudWatch logs from Uvicorn; trace LLM latency separately (LiteLLM provider dashboards).

The published `seal/api` image does **not** include the Lambda adapter by default; add it in a private fork or multi-stage build when you need dual ECS + Lambda deploys.
