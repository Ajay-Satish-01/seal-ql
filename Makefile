.PHONY: up down build test test-cov logs shell lint format seed setup check ci help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ============================================================
# Docker Stack
# ============================================================

up: ## Start the entire dev stack
	docker compose up --build -d
	@echo "\n✅ Stack is running (Dev Mode)!"
	@echo "   API:      http://localhost:8000"
	@echo "   Docs:     http://localhost:8000/docs"
	@echo "   Postgres: localhost:5432"
	@echo "   Ollama:   http://localhost:11434"

down: ## Stop the stack
	docker compose down

docker-build: ## Build the production Docker image
	docker build --target prod -t intelligence-connector/api:latest -f apps/api/Dockerfile .

docker-push: docker-build ## Push the production Docker image to DockerHub
	docker push intelligence-connector/api:latest

build: ## Rebuild all containers
	docker compose build --no-cache

logs: ## Tail API logs
	docker compose logs -f api

shell: ## Open a shell in the API container
	docker compose exec api /bin/bash

# ============================================================
# Testing
# ============================================================

test: ## Run all tests (pass ARGS= for specific tests)
	docker compose exec api uv run pytest $(ARGS) -v

test-cov: ## Run tests with coverage report
	docker compose exec api uv run pytest --cov --cov-report=html --cov-report=term -v

test-sdk: ## Run TS SDK tests locally
	cd sdks/typescript && pnpm test

openapi: ## Generate OpenAPI json spec
	docker compose run --rm -T api uv run python scripts/generate_openapi.py

# ============================================================
# Linting & Formatting (Docker-first)
# ============================================================

lint: ## Run all linters (Python + TS)
	@echo "🐍 Ruff lint..."
	docker compose run --rm -T api uv run ruff check .
	@echo "\n✅ All linters passed"

format: ## Auto-format all code (Python + TS)
	@echo "🐍 Ruff format..."
	docker compose run --rm -T api uv run ruff format .
	@echo "🐍 Ruff fix..."
	docker compose run --rm -T api uv run ruff check --fix .
	@echo "\n✅ All code formatted"

check: ## Run all checks (lint + format check + tests) — same as CI
	@echo "═══════════════════════════════════════"
	@echo "  Running full CI check suite"
	@echo "═══════════════════════════════════════"
	@echo "\n📋 1/4 — Ruff lint..."
	docker compose run --rm -T api uv run ruff check .
	@echo "\n📋 2/4 — Ruff format check..."
	docker compose run --rm -T api uv run ruff format --check .
	@echo "\n📋 3/4 — Tests..."
	docker compose run --rm -T api uv run pytest -v --tb=short
	@echo "\n📋 4/4 — Prod Image Build..."
	docker build --target prod -t intelligence-connector/api:test -f apps/api/Dockerfile .
	@echo "\n═══════════════════════════════════════"
	@echo "  ✅ All checks passed!"
	@echo "═══════════════════════════════════════"

# ============================================================
# Setup & Data
# ============================================================

setup: ## First-time setup: install pre-commit hooks
	pip install pre-commit
	pre-commit install
	pre-commit install --hook-type pre-push
	@echo "\n✅ Pre-commit hooks installed!"
	@echo "   - pre-commit: ruff lint + format, prettier, eslint"
	@echo "   - pre-push: pytest"

seed: ## Re-run the database seed script
	docker compose exec -T postgres psql -U postgres -d intelligence_connector < scripts/seed.sql

ci: check ## Alias for 'check' — mirrors CI pipeline locally
