# Deployment Guide (Self-Hosting)

The Intelligence Connector provides an easy-to-deploy, Docker-first architecture for hosting your own SQL agent and API gateway.

## Architecture

The stack consists of:

1. **API** — FastAPI backend (query planner, SQL execution, charts).
2. **Postgres** — TimescaleDB for analytics (bundled in compose).
3. **Ollama** — Local LLM (optional; skipped when `OLLAMA_PROFILE=disabled`).

## Prerequisites

- Docker and Docker Compose
- Ports `8000`, `5432`, and (for Ollama) `11434` available

## Quick Start (Local Development)

```bash
make up      # starts Ollama when OLLAMA_PROFILE is default
make seed
curl http://localhost:8000/health
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

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Postgres/asyncpg connection string | `postgresql+asyncpg://…` |
| `OLLAMA_PROFILE` | `default` = local Ollama; `disabled` = cloud LLM | `default` |
| `LLM_MODEL` | LiteLLM model id (`ollama/…`, `gemini/…`, etc.) | `ollama/llama3.2:1b` |
| `LLM_BASE_URL` | Ollama URL (ignored when `OLLAMA_PROFILE=disabled`) | `http://ollama:11434` |
| `LLM_API_KEY` | Cloud API key (or use `GEMINI_API_KEY`, etc.) | — |
| `CORS_ORIGINS` | JSON array of allowed browser origins | `["http://localhost:3000"]` |
| `MAX_ROWS` | Row cap for generated SQL | `10000` |

The API logs **warnings** at startup for common misconfigurations (e.g. cloud model without `OLLAMA_PROFILE=disabled`, or legacy `LLM_TYPE` in `.env`).

### Standalone `docker run` (cloud)

```bash
docker run -d -p 8000:8000 \
  -e OLLAMA_PROFILE=disabled \
  -e DATABASE_URL="postgresql+asyncpg://user:pass@dbhost/mydb" \
  -e LLM_MODEL="gemini/gemini-1.5-flash" \
  -e LLM_API_KEY="your-key" \
  intelligence-connector/api:latest
```

## Health Checks

The production image health-checks `GET /health`. Use the same endpoint in your load balancer.
