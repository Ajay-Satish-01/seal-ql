# 🌌 Intelligence Connector

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

An **AI-powered SQL query generation, validation, and visualization SDK** enabling natural language querying over multi-dialect databases with robust client/server safety and native visual chart rendering.

```ts
// Express your data questions in natural language:
const result = await sdk.query("Monthly revenue trends by region");

console.log(result.sql);        // Validated, safe, optimized SQL
console.log(result.data);       // Executed database results
console.log(result.chartSpec);  // Custom Vega-Lite visualization spec
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
       │          (FastAPI / Uvicorn)            │
       └────────────────────┬────────────────────┘
                            │
                            ▼
       ┌─────────────────────────────────────────┐
       │            Query Planner (LLM)          │
       │     (LiteLLM + Instructor + Ollama)    │
       └────────────────────┬────────────────────┘
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

* **Advanced Schema Introspection**: Deep introspection covering normal tables, database views, materialized views, foreign/primary key constraints, and TimescaleDB-specific features (hypertables, continuous aggregations) with automatic extension detection.
* **Dialect Intrinsic Execution**: Optimized schema processing and generation for **Postgres (with full TimescaleDB aggregates)** and **DuckDB (highly optimized analytics)**.
* **Local-First & Production-Ready**: Orchestrated using Docker Compose with local LLM integration via **Ollama** by default.
* **Modern Tooling & Environments**: Package structures utilizing `uv` workspaces for Python packages/applications, and modern typescript modules using `pnpm`.
* **Zero-Trust SQL Safety**: SQLGlot-based AST safety checker to block destructive statements and enforce pagination limits.

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
# Start all services (API, Postgres with TimescaleDB, Ollama)
make up
```

Once running, the stack exposes:
* **API Server**: `http://localhost:8000`
* **Swagger/OpenAPI docs**: `http://localhost:8000/docs`
* **Postgres Database**: `localhost:5432` (User: `postgres`, Pass: `postgres`, DB: `intelligence_connector`)
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

We maintain a strict quality gate in development using pre-commit hooks to format, lint, and run tests before any code leaves your local environment.

### First-Time Hook Setup
Run the setup utility to install pre-commit and pre-push hooks:
```bash
make setup
```

Once registered:
* **Pre-commit hooks** auto-execute on `git commit`:
  * Python files are reformatted and linted using `ruff` (extremely fast!).
  * TypeScript files are formatted with `prettier` and linted with `eslint`.
  * Standard file sanity checks are done (JSON, TOML, YAML parsing, merge conflict resolution).
* **Pre-push hooks** auto-execute on `git push`:
  * Runs all python tests locally via `uv run pytest`.

To run all formatting and linting controls manually:
```bash
# Run pre-commit checks manually on all files
pre-commit run --all-files
```

---

## 🗂️ Project Directory Structure

```text
├── apps
│   └── api/                     # FastAPI back-end service
├── packages
│   ├── core/                    # Core Models, Introspection & Planner
│   ├── sql/                     # Dialect Validators & AST Safety checkers
│   ├── charts/                  # Vega-Lite Spec Generators
│   └── semantic/                # Semantic metrics registries
├── sdks
│   ├── python/                  # Python SDK wrapper
│   └── typescript/              # TypeScript SDK wrapper
├── scripts
│   └── seed.sql                 # TimescaleDB & Postgres analytics schema seed
├── pyproject.toml               # Master uv Workspace Configuration
└── docker-compose.yml           # Core Docker services manifest
```

---

## 📜 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
