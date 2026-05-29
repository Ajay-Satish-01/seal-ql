# Deployment Guide (Self-Hosting)

The Intelligence Connector provides an easy-to-deploy, Docker-first architecture for hosting your own SQL agent and API gateway.

## Architecture

The stack consists of three main components when run locally:
1. **API**: FastAPI backend running the Query Planner and Executer.
2. **Postgres**: (TimescaleDB) The default target database for analytics.
3. **Ollama**: Local LLM execution (default is `llama3.2:1b`).

## Prerequisites
- Docker & Docker Compose
- Ensure ports `8000`, `5432`, and `11434` are available.

## Quick Start (Local Development)

```bash
# Start all services (builds the image in `dev` mode)
make up

# Seed the database with mock schema/data
make seed

# Check the API is healthy
curl http://localhost:8000/health
```

## Production Deployment

The provided `Dockerfile` uses a multi-stage build. By default, `make docker-build` targets the `prod` stage which strips out development dependencies and uses a non-root user.

### 1. Build the Production Image

```bash
make docker-build
```

### 2. Environment Variables

The `api` container relies on environment variables defined via `pydantic-settings`.
Key variables to provide in production:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Target database connection string (Postgres format). | `postgresql+asyncpg://...` |
| `DUCKDB_PATH` | Path to duckdb file if using duckdb. | `:memory:` |
| `LLM_MODEL` | The LLM to use (e.g. `gpt-4o`, `ollama/llama3.2`). | `ollama/llama3.2:1b` |
| `LLM_BASE_URL` | Base URL for LLM provider (if applicable). | `http://ollama:11434` |
| `LLM_API_KEY` | API key if using OpenAI/Anthropic/etc. | `None` |
| `CORS_ORIGINS` | JSON list of allowed origins. | `["http://localhost:3000"]` |
| `MAX_ROWS` | Row limit for LLM generated SQL. | `10000` |

### 3. Running in Production

Use your orchestrator of choice (Docker Compose, Kubernetes, ECS, etc).

For a standalone docker run:

```bash
docker run -d -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://prod_user:pass@dbhost/mydb" \
  -e LLM_MODEL="gpt-4o" \
  -e LLM_API_KEY="sk-..." \
  intelligence-connector/api:latest
```

## Health Checks

The production Dockerfile includes a built-in `HEALTHCHECK` running against `http://localhost:8000/health`.
You can also use this endpoint in your load balancer or orchestration tool.
