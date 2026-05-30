.PHONY: up down build test test-cov logs shell lint format seed setup check ci help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ============================================================
# Docker Stack
# ============================================================

up: ## Start the entire dev stack
	@if [ "$${OLLAMA_PROFILE:-default}" = "disabled" ]; then \
		docker compose up --build -d; \
	else \
		COMPOSE_PROFILES=default docker compose up --build -d; \
	fi
	@echo "\n✅ Stack is running (Dev Mode)!"
	@echo "   API:      http://localhost:8000"
	@echo "   Docs:     http://localhost:8000/docs"
	@echo "   Postgres: localhost:5432"
	@if [ "$${OLLAMA_PROFILE:-default}" != "disabled" ]; then \
		echo "   Ollama:   http://localhost:$${OLLAMA_PORT:-11434}"; \
	else \
		echo "   Ollama:   (disabled — cloud LLM mode)"; \
	fi

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

openapi: ## Generate OpenAPI json/yaml spec
	uv run python scripts/generate_openapi.py

web-fixtures: ## Generate demo fixtures for apps/web
	uv run python scripts/generate_web_demo_fixtures.py

sync-docs-assets: openapi web-fixtures ## Copy seed.sql and OpenAPI into docs site
	mkdir -p apps/web/public/samples apps/web/src/data
	cp scripts/seed.sql apps/web/public/samples/seed.sql
	cp apps/api/openapi.json apps/web/src/data/openapi.json
	cp apps/api/openapi.json apps/web/public/openapi.json
	@echo "✅ Synced docs assets (seed.sql, openapi.json)"

verify-openapi-sync: openapi ## Fail if committed OpenAPI copies differ from generated
	cp apps/api/openapi.json apps/web/src/data/openapi.json
	cp apps/api/openapi.json apps/web/public/openapi.json
	@git diff --exit-code apps/api/openapi.json apps/web/src/data/openapi.json apps/web/public/openapi.json \
		|| (echo "\n❌ OpenAPI out of sync. Run: make sync-docs-assets" && exit 1)
	@echo "✅ OpenAPI copies are in sync"

validate-query: ## Validate live POST /v1/query (ARGS="base_url query")
	uv run python scripts/validate_query_response.py $(ARGS)

check-web: ## Build the docs/demo Next.js app
	cd apps/web && pnpm install --frozen-lockfile && pnpm build

# ============================================================
# Linting & Formatting (Docker-first)
# ============================================================

lint: ## Run all linters (Python + TS)
	@echo "🐍 Ruff lint..."
	docker compose run --rm -T api uv run ruff check .
	@echo "🟦 TS ESLint..."
	cd sdks/typescript && pnpm exec eslint . --max-warnings=0
	@echo "\n✅ All linters passed"

format: ## Auto-format all code (Python + TS)
	@echo "🐍 Ruff format..."
	docker compose run --rm -T api uv run ruff format .
	@echo "🐍 Ruff fix..."
	docker compose run --rm -T api uv run ruff check --fix .
	@echo "🟦 TS Prettier..."
	cd sdks/typescript && pnpm run format
	@echo "\n✅ All code formatted"

check: ## Run all checks (lint + format check + tests) — same as CI
	@echo "═══════════════════════════════════════"
	@echo "  Running full CI check suite"
	@echo "═══════════════════════════════════════"
	@echo "\n📋 1/9 — Ruff fix & lint..."
	docker compose run --rm -T api uv run ruff check --fix .
	@echo "\n📋 2/9 — Ruff format..."
	docker compose run --rm -T api uv run ruff format .
	@echo "\n📋 3/9 — TS ESLint & Prettier..."
	cd sdks/typescript && pnpm run lint && pnpm run format
	@echo "\n📋 4/9 — Python Tests..."
	docker compose run --rm -T api uv run pytest -v --tb=short \
		--ignore=sdks/python/tests/test_sdk_e2e.py \
		--ignore=apps/api/tests/test_e2e.py
	@echo "\n📋 5/9 — Demo fixture validation..."
	uv run pytest tests/test_response_validation.py -v --tb=short
	@echo "\n📋 6/9 — OpenAPI docs sync..."
	$(MAKE) verify-openapi-sync
	@echo "\n📋 7/9 — Web app build..."
	$(MAKE) check-web
	@echo "\n📋 8/9 — TS SDK tests..."
	cd sdks/typescript && pnpm test
	@echo "\n📋 9/9 — Prod Image Build..."
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
