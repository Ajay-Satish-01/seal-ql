.PHONY: up down build test test-cov logs shell lint format seed setup check ci help eval eval-planner eval-local eval-compare

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ============================================================
# Docker Stack
# ============================================================

up: ## Start the entire dev stack
	@if [ ! -f .env ]; then \
		echo "❌ Missing .env — run: cp .env.example .env"; \
		exit 1; \
	fi
	@if ! grep -qE '^SEAL_API_KEY=.+' .env 2>/dev/null; then \
		echo "❌ Set SEAL_API_KEY in .env (see .env.example; use: openssl rand -hex 32)"; \
		exit 1; \
	fi
	@SEAL_EXTRA=$$(grep -E '^SEAL_EXTRA=' .env 2>/dev/null | cut -d= -f2-); \
	if [ -z "$$SEAL_EXTRA" ] && grep -qE '^VECTOR_STORE=chroma' .env 2>/dev/null; then \
	  SEAL_EXTRA=chroma; \
	  echo "ℹ️  VECTOR_STORE=chroma — building API with SEAL_EXTRA=chroma"; \
	fi; \
	export SEAL_EXTRA; \
	if [ "$${OLLAMA_PROFILE:-default}" = "disabled" ]; then \
	  docker compose up --build -d; \
	else \
	  COMPOSE_PROFILES=default docker compose up --build -d; \
	fi
	@echo "\n✅ Stack is running (Dev Mode)!"
	@echo "   API:         http://localhost:8000"
	@echo "   API Swagger: http://localhost:8000/docs"
	@echo "   Docs site:   http://localhost:3000  (cd apps/docs && pnpm dev)"
	@echo "   Dashboard:   http://localhost:3001  (cd apps/web && pnpm dev)"
	@echo "   Postgres:    localhost:5432"
	@if [ "$${OLLAMA_PROFILE:-default}" != "disabled" ]; then \
		echo "   Ollama:      http://localhost:$${OLLAMA_PORT:-11434}"; \
	else \
		echo "   Ollama:      (disabled — cloud LLM mode)"; \
	fi

down: ## Stop the stack
	docker compose down

VERSION ?= 0.1.0
IMAGE ?= seal/api

docker-build: ## Build the production Docker image (VERSION=0.1.0; SEAL_EXTRA=chroma for Chroma RAG)
	docker build --target prod \
		--build-arg SEAL_EXTRA=$(SEAL_EXTRA) \
		-t $(IMAGE):$(VERSION) \
		-t $(IMAGE):latest \
		-f apps/api/Dockerfile .

docker-push: docker-build ## Push the production Docker image to Docker Hub
	docker push $(IMAGE):$(VERSION)
	docker push $(IMAGE):latest

sdk-python-build: ## Build Python SDK wheel/sdist for PyPI
	uv build --package seal

sdk-npm-pack: ## Dry-run npm pack for the TypeScript SDK
	cd sdks/typescript && pnpm install --frozen-lockfile && pnpm build && pnpm pack --dry-run

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

openapi-ts: openapi ## Generate TypeScript types from OpenAPI (SDK)
	cd sdks/typescript && pnpm install --frozen-lockfile && pnpm run generate:api-types

sync-catalog: ## Sync data catalog YAML from live database schema
	uv run python scripts/sync_catalog.py

docs-fixtures: ## Generate demo fixtures for apps/docs
	uv run python scripts/generate_web_demo_fixtures.py

sync-docs-assets: openapi docs-fixtures ## Copy seed.sql and OpenAPI into docs site
	mkdir -p apps/docs/public/samples apps/docs/src/data
	cp scripts/seed.sql apps/docs/public/samples/seed.sql
	cp apps/api/openapi.json apps/docs/src/data/openapi.json
	cp apps/api/openapi.json apps/docs/public/openapi.json
	mkdir -p apps/docs/public/config
	cp -f config/seal-tools.openai.json apps/docs/public/seal-tools.openai.json
	cp -f config/catalog.example.yaml apps/docs/public/config/catalog.example.yaml
	@echo "✅ Synced docs assets (seed.sql, openapi.json, seal-tools, catalog.example)"

verify-dependency-catalog: ## Fail if JS/Python manifests drift from config/dependency-catalog.yaml
	uv run python scripts/verify_dependency_catalog.py

verify-rate-limit-sync: ## Fail if rate_limit_markers.json copies drift from config/
	uv run python scripts/verify_rate_limit_sync.py

verify-openapi-sync: openapi-ts ## Fail if committed OpenAPI + SDK types differ from generated
	@test -f sdks/typescript/src/generated/openapi.ts || (echo "❌ Missing sdks/typescript/src/generated/openapi.ts — run: make openapi-ts" && exit 1)
	cp apps/api/openapi.json apps/docs/src/data/openapi.json
	cp apps/api/openapi.json apps/docs/public/openapi.json
	@git diff --exit-code apps/api/openapi.json apps/api/openapi.yaml \
		apps/docs/src/data/openapi.json apps/docs/public/openapi.json \
		sdks/typescript/src/generated/openapi.ts \
		|| (echo "\n❌ OpenAPI out of sync. Run: make sync-docs-assets && make openapi-ts" && exit 1)
	@echo "✅ OpenAPI spec, docs copies, and SDK openapi-typescript output are in sync"

validate-query: ## Validate live POST /v1/query (ARGS="base_url query")
	uv run python scripts/validate_query_response.py $(ARGS)

check-docs: ## Build the docs/marketing Next.js app (port 3000)
	cd apps/docs && pnpm install --frozen-lockfile && pnpm run verify:doc-snippets && pnpm build

check-dashboard: ## Build the operational dashboard (port 3001)
	cd apps/web && pnpm install --frozen-lockfile && pnpm build

check-web: check-docs ## Alias for docs app build

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
	@echo "\n📋 1/12 — Ruff fix & lint..."
	docker compose run --rm -T api uv run ruff check --fix .
	@echo "\n📋 2/12 — Ruff format..."
	docker compose run --rm -T api uv run ruff format .
	@echo "\n📋 3/12 — TS ESLint & Prettier..."
	cd sdks/typescript && pnpm run lint && pnpm run format
	@echo "\n📋 4/12 — Python Tests..."
	docker compose run --rm -T api uv sync --frozen --all-packages
	docker compose run --rm -T api uv run pytest -v --tb=short \
		--ignore=sdks/python/tests/test_sdk_e2e.py \
		--ignore=apps/api/tests/test_e2e.py \
		--ignore=apps/api/tests/test_catalog_workspace_integration.py \
		--ignore=tests/test_response_validation.py
	@echo "\n📋 5/12 — Demo fixture & metadata contract validation..."
	uv run pytest tests/test_response_validation.py packages/core/tests/test_chat_flatten_contract.py -v --tb=short
	cd apps/docs && pnpm run verify:chat-flatten && pnpm run verify:stream-meta
	@echo "\n📋 6/12 — Dependency catalog..."
	$(MAKE) verify-dependency-catalog
	@echo "\n📋 7/12 — Rate-limit marker sync..."
	$(MAKE) verify-rate-limit-sync
	@echo "\n📋 8/12 — OpenAPI docs sync..."
	$(MAKE) verify-openapi-sync
	@echo "\n📋 9/12 — Docs app build..."
	$(MAKE) check-docs
	@echo "\n📋 10/12 — Dashboard app build..."
	$(MAKE) check-dashboard
	@echo "\n📋 11/12 — TS SDK tests..."
	cd sdks/typescript && pnpm test
	@echo "\n📋 12/12 — Prod Image Build..."
	docker build --target prod -t seal/api:test -f apps/api/Dockerfile .
	@echo "\n═══════════════════════════════════════"
	@echo "  ✅ All checks passed!"
	@echo "═══════════════════════════════════════"

# ============================================================
# Setup & Data
# ============================================================

setup: ## First-time setup: install pre-commit hooks
	pip install pre-commit
	pre-commit install
	@echo "\n✅ Pre-commit hooks installed!"
	@echo "   - pre-commit: ruff lint + format, prettier, eslint, conventional commit messages"
	@echo "   - tests: GitHub Actions + make check (unit) / make check-e2e (live E2E)"

seed: ## Re-apply demo data (truncates orders/events, re-seeds; CAGG refresh runs at end of seed.sql)
	docker compose exec -T postgres psql -U postgres -d seal < scripts/truncate_demo_data.sql
	docker compose exec -T postgres psql -U postgres -d seal < scripts/seed.sql

refresh-cagg: ## Refresh Timescale continuous aggregates (events_hourly, events_daily)
	docker compose exec -T postgres psql -U postgres -d seal < scripts/refresh_continuous_aggregates.sql
	@echo "ℹ️  Apply workspace schema: docker compose exec -T postgres psql -U postgres -d seal < scripts/migrate_app.sql"

EVAL_DB_URL ?= postgresql+asyncpg://postgres:postgres@postgres:5432/seal
EVAL_MIN_RATE_FLAG = --min-execution-rate $${EVAL_MIN_RATE:-0.6}
EVAL_RUNNER = docker compose exec -T api uv run python evals/seal_evals/runner.py

# eval / eval-planner: shell DATABASE_URL (compose env). Host target uses Make variable ARGS (see below).
eval: ## Local only: planner evals on seeded Postgres in Docker (`make up` + `make seed`; not in PR CI)
	$(EVAL_RUNNER) $${DATABASE_URL:-$(EVAL_DB_URL)} $(EVAL_MIN_RATE_FLAG)

eval-planner: ## Local only: validation-only planner eval (no execution); see docs/local-evals.md
	$(EVAL_RUNNER) $${DATABASE_URL:-$(EVAL_DB_URL)} --planner-only $(EVAL_MIN_RATE_FLAG)

# Must match DEFAULT_EVAL_DATABASE_URL in evals/seal_evals/runner.py (see evals/tests/test_runner.py)
EVAL_HOST_DB_URL ?= postgresql+asyncpg://postgres:postgres@localhost:5432/seal

eval-local: ## Local only: run eval runner on host (ARGS=DB URL; EVAL_PLANNER=1 for validation-only)
	uv run python evals/seal_evals/runner.py \
		$(or $(ARGS),$(EVAL_HOST_DB_URL)) \
		$(if $(EVAL_PLANNER),--planner-only,) $(EVAL_MIN_RATE_FLAG)

eval-compare: ## Local only: matrix compare (MODELS=m1,m2; DIALECT_URLS=url1,url2; EVAL_PLANNER=1)
	uv run python evals/seal_evals/runner.py \
		$(or $(ARGS),$(EVAL_HOST_DB_URL)) \
		$(if $(MODELS),--models $(MODELS),) \
		$(if $(DIALECT_URLS),--dialect-urls $(DIALECT_URLS),) \
		$(if $(EVAL_PLANNER),--planner-only,) $(EVAL_MIN_RATE_FLAG)

check-e2e: ## Run live E2E tests (requires `make up` + `make seed`)
	@echo "E2E — waiting for API on :8000..."
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do \
	  if curl -sf http://localhost:8000/health | grep -q '"status":"ok"'; then break; fi; \
	  if [ $$i -eq 30 ]; then echo "❌ API not healthy — run: make up"; exit 1; fi; \
	  sleep 2; \
	done
	docker compose exec -T api uv run pytest -v --tb=short \
		sdks/python/tests/test_sdk_e2e.py \
		apps/api/tests/test_e2e.py \
		apps/api/tests/test_catalog_workspace_integration.py
	cd sdks/typescript && SEAL_API_KEY=$${SEAL_API_KEY:-seal-ci-test-api-key-0123456789abcdef0123456789abcdef} pnpm test
	@echo "✅ E2E tests passed"

ci: check ## Lint, unit tests, builds (same as CI unit jobs; run `make check-e2e` for live HTTP E2E)
