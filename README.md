# 🌌 Seal

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

An **AI-powered SQL query generation, validation, and visualization SDK** with **schema-grounded conversational Q&A** — natural language over multi-dialect databases, zero-trust SQL safety, optional Vega-Lite charts, and agent-framework-compatible HTTP tools.

```ts
import { Seal } from "seal";

const client = new Seal({
  baseUrl: "http://localhost:8000",
  apiKey: process.env.SEAL_API_KEY,
});

// One-shot analytics (always returns a chart when applicable)
const result = await client.query("Monthly revenue trends by region");
console.log(result.sql, result.results, result.chart);

// Multi-turn Q&A with optional charts and streaming
const chat = await client.chat("What drove revenue last quarter?", {
  includeCharts: true,
  sessionId: "user-123",
});
console.log(chat.message, chat.sql);
```

---

## 🏛️ System Architecture

```text
       ┌─────────────────────────────────────────┐
       │             Frontend / SDKs             │
       │        (TypeScript / Python Clients)    │
       └────────────────────┬────────────────────┘
                            │ (JSON over HTTP/gRPC)
                            ▼
       ┌─────────────────────────────────────────┐
       │             API Gateway                 │
       │   /v1/query · /v1/chat · /v1/catalog   │
       └────────────────────┬────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
       ┌──────────────┐           ┌──────────────────┐
       │ ChatService  │           │ Query Planner    │
       │ + Enhancers  │           │ (LiteLLM +       │
       │ + Sessions   │           │  Instructor)     │
       └──────┬───────┘           └────────┬─────────┘
              │                            │
              └─────────────┬──────────────┘
                            ▼
       ┌─────────────────────────────────────────┐
       │     Shared SQL pipeline + Data catalog   │
       └────────────────────┬────────────────────┘
                            ▼
                            │
                            ▼
       ┌─────────────────────────────────────────┐
       │              SQL Validator              │
       │     (SQLGlot AST Validation & Safety)   │
       └────────────────────┬────────────────────┘
                            │
                            ▼
       ┌─────────────────────────────────────────┐
       │            Database Executor            │
       │       (DuckDB / Postgres / Timescale)   │
       └────────────────────┬────────────────────┘
                            │
                            ▼
       ┌─────────────────────────────────────────┐
       │          Chart Spec Generator           │
       │      (Heuristic Vega-Lite Spec)         │
       └─────────────────────────────────────────┘
```

---

## 🚀 Key Features

* **Schema-Grounded Chat (Q&A)**: `POST /v1/chat` with session memory, prompt enhancement (schema + optional vector RAG + multi-turn), SSE streaming, and optional charts via `include_charts`.
* **Global Data Catalog**: Auto-synced YAML (`config/catalog.yaml`) with business descriptions injected into query, chat, and planner paths; `GET /v1/catalog` and `POST /v1/catalog/sync`.
* **Advanced Schema Introspection**: Deep introspection covering normal tables, database views, materialized views, foreign/primary key constraints, and TimescaleDB-specific features (hypertables, continuous aggregations) with automatic extension detection.
* **Semantic Metric Layer**: Map raw schema structures to business logic with declarative YAML metric/dimension models to enhance LLM context accuracy.
* **Self-Healing Repair Loops**: Automatic validation and execution error recovery that feeds exact dialect errors back into the LLM planner for multi-turn SQL correction.
* **Dialect Intrinsic Execution**: Optimized schema processing and generation for **Postgres (with full TimescaleDB aggregates)** and **DuckDB (highly optimized analytics)**.
* **Local-First & Production-Ready**: Orchestrated using Docker Compose with local LLM integration via **Ollama** by default.
* **Modern Tooling & Environments**: Package structures utilizing `uv` workspaces for Python packages/applications, and modern typescript modules using `pnpm`.
* **Zero-Trust SQL Safety**: SQLGlot-based AST safety checker to block destructive statements and enforce pagination limits.
* **API Key Authentication**: Shared `X-API-Key` for `/v1/*` with production-safe env validation (`SEAL_AUTH_REQUIRED`, `SEAL_DEV_MODE`, `SEAL_DISABLE_DOCS`).
* **LLM Guardrails**: Scope gate on `/v1/query` and `/v1/chat` — in-scope analytics/schema only; chat returns HTTP 200 with `metadata.suggested_queries` on refusal; query returns HTTP 400 with structured `detail` (`query_out_of_scope`, `reason`, up to three `suggested_queries`). SDKs raise `QueryOutOfScopeError` on query guardrails failures.
* **Workspace API**: Hot-reload guardrails and chat settings in dev; catalog description overrides; vector reindex.
* **Automated Evaluations**: Built-in eval runners to measure SQL syntax success, execution rates, and planner repair metrics against DuckDB and TimescaleDB test cases.

---

## 🛠️ Quick Start & Installation

### Prerequisites

Ensure you have the following installed on your machine:
* [Docker & Docker Compose](https://docs.docker.com/get-docker/)
* [uv](https://github.com/astral-sh/uv) (Python package installer & environment manager)
* [pnpm](https://pnpm.io/) (Fast, disk space efficient package manager)
* [pre-commit](https://pre-commit.com/) (Required for local code validation)

---

### 📦 1. Spin Up Dev Stack (Docker First)

Use the automated Makefile controls to orchestrate your local environment:

```bash
# First time: copy env template (sets SEAL_DEV_MODE=true and a placeholder API key for local dev)
cp .env.example .env

# Start all services (API, Postgres with TimescaleDB, Ollama)
make up
```

For production-style auth (`SEAL_AUTH_REQUIRED`, generated `SEAL_API_KEY`), see [SETUP.md](./SETUP.md) and the docs site **Authentication** page.

Once running, the stack exposes:
* **API Server**: `http://localhost:8000` (Swagger at `/docs`)
* **Docs site** (`apps/docs`): `http://localhost:3000` — run `cd apps/docs && pnpm dev`
* **Dashboard** (`apps/web`): `http://localhost:3001` — run `cd apps/web && pnpm dev`
* **Postgres Database**: `localhost:5432` (User: `postgres`, Pass: `postgres`, DB: `seal`)
* **Ollama Service**: `http://localhost:11434`

To stop the services:
```bash
make down
```

---

### 🧩 2. Populate Database Seed

Seed Postgres with a production-grade analytics schema (containing normal tables, materialized views, TimescaleDB hypertables, and continuous aggregates) to test introspection:

```bash
make seed
```

Optional: sync the data catalog from the live schema (also runs on API startup when `CATALOG_AUTO_SYNC=true`):

```bash
make sync-catalog
```

Try chat (requires `SEAL_API_KEY` in `.env` when auth is enabled):

```bash
curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SEAL_API_KEY" \
  -d '{"message":"What tables exist?"}' | jq .
```

---

### 🐍 3. Python Local Environment Setup

Create a highly optimized, unified development environment using `uv`:

```bash
# Install dependencies, resolve workspaces, and build editable modules
uv sync --all-packages --all-extras
```

You can now run Python unit tests, command-line utilities, or code validation manually in your local environment:

```bash
# Run pytest locally
uv run pytest -v
```

---

### 📦 4. TypeScript Local Environment Setup

Set up the TypeScript SDK module workspace:

```bash
# Navigate to typescript SDK
cd sdks/typescript

# Install dependencies and local tools
pnpm install
```

---

## 🎨 Development & CI/CD Checks

We maintain a strict quality gate using pre-commit hooks for format/lint on commit, and GitHub Actions for tests (unit + live E2E).

### First-Time Hook Setup
Run the setup utility to install pre-commit hooks:
```bash
make setup
```

Once registered:
* **Pre-commit hooks** auto-execute on `git commit`:
  * Python files are reformatted and linted using `ruff` (extremely fast!).
  * TypeScript files are formatted with `prettier` and linted with `eslint`.
  * Standard file sanity checks are done (JSON, TOML, YAML parsing, merge conflict resolution).
  * Commit messages are validated as [Conventional Commits](https://www.conventionalcommits.org/) (e.g. `feat: add workspace API`, `fix(api): handle empty catalog`).
* **Tests** run in CI on every PR (`Python — Tests` + `E2E Tests`). Locally: `make check` (unit, OpenAPI sync, metadata contract checks, docs/dashboard builds) and `make check-e2e` (live stack).
* **API types** — After changing Pydantic models in `apps/api/app/schemas.py`, run `make openapi-ts` and commit `apps/api/openapi.{json,yaml}`, docs OpenAPI copies, and `sdks/typescript/src/generated/openapi.ts`. CI enforces via `make verify-openapi-sync`.

To run all formatting and linting controls manually:
```bash
# Run pre-commit checks manually on all files
pre-commit run --all-files
```

---

## 🗂️ Project Directory Structure

```text
├── apps
│   ├── api/                     # FastAPI back-end service
│   ├── docs/                    # Docs site + /demo (port 3000)
│   └── web/                     # Operational dashboard (port 3001)
├── packages
│   ├── core/                    # Planner, chat, catalog, enhancement, vector RAG
│   ├── sql/                     # Dialect Validators & AST Safety checkers
│   ├── charts/                  # Vega-Lite Spec Generators
│   └── semantic/                # Semantic metrics registries
├── config
│   ├── catalog.example.yaml     # Sample data catalog (descriptions)
│   ├── seal-tools.openai.json   # OpenAI tool manifest for agents
│   └── stream_meta_metadata_keys.json  # Shared metadata key manifest (Python + TS)
├── shared/                      # Cross-app TS: stream-meta, metadata-contract (docs + dashboard)
├── docs
│   ├── chat-metadata.md         # Query/chat execution metadata (JSON vs SSE)
│   ├── chat-enhancement.md      # Prompt enhancer chain (contributors)
│   ├── guardrails.md            # Scope gate (contributors)
│   ├── workspace-api.md         # Workspace settings API (contributors)
│   └── integrations/            # Vector stores, agent frameworks, custom enhancers
├── sdks
│   ├── python/                  # Python SDK wrapper
│   └── typescript/              # TypeScript SDK (OpenAPI-generated types + vendored shared/)
├── scripts
│   ├── seed.sql                 # TimescaleDB & Postgres analytics schema seed
│   ├── generate_openapi.py      # OpenAPI spec + injected SSE/chat component schemas
│   └── sync_catalog.py          # CLI catalog sync
├── pyproject.toml               # Master uv Workspace Configuration
└── docker-compose.yml           # Core Docker services manifest
```

---

## 📡 API surface

| Endpoint | Purpose |
| -------- | ------- |
| `POST /v1/query` | Natural language → validated SQL, results, chart; guardrails OOS → 400 structured `detail` |
| `POST /v1/chat` | Conversational Q&A (`session_id`, `include_charts`, `stream`, `enhancement`); OOS → 200 refusal + `metadata.suggested_queries` |
| `GET /v1/catalog` | Global data catalog (business descriptions) |
| `POST /v1/catalog/sync` | Re-sync catalog YAML from live schema |
| `PATCH /v1/catalog/descriptions` | Table/view description overrides |
| `GET /v1/schema` | Introspected database schema |
| `GET` / `PATCH /v1/workspace/settings` | Workspace settings (guardrails, chat, vector) |
| `GET /v1/workspace/export` | Export settings + catalog overrides |
| `POST /v1/vector/reindex` | Rebuild vector index |

User-facing guides: docs site at `http://localhost:3000` (`/docs/how-it-works`, `/docs/execution-metadata`, `/docs/configuration`, `/docs/guardrails`), dashboard at `http://localhost:3001`, plus [SETUP.md](SETUP.md), [docs/how-seal-works.md](docs/how-seal-works.md), [docs/chat-metadata.md](docs/chat-metadata.md), and [DEPLOYMENT.md](DEPLOYMENT.md).

## 📦 Publishing

Self-host with Docker (`seal/api`), or install the SDKs from PyPI/npm as `seal`. See [RELEASING.md](RELEASING.md), [SETUP.md](SETUP.md), and [DEPLOYMENT.md](DEPLOYMENT.md).

## 📜 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
