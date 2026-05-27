.PHONY: up down build test test-cov logs shell lint format seed help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Start the entire dev stack
	docker compose up --build -d
	@echo "\n✅ Stack is running!"
	@echo "   API:      http://localhost:8000"
	@echo "   Docs:     http://localhost:8000/docs"
	@echo "   Postgres: localhost:5432"
	@echo "   Ollama:   http://localhost:11434"

down: ## Stop the stack
	docker compose down

build: ## Rebuild all containers
	docker compose build --no-cache

test: ## Run all tests (pass ARGS= for specific tests)
	docker compose exec api uv run pytest $(ARGS) -v

test-cov: ## Run tests with coverage report
	docker compose exec api uv run pytest --cov --cov-report=html --cov-report=term -v

logs: ## Tail API logs
	docker compose logs -f api

shell: ## Open a shell in the API container
	docker compose exec api /bin/bash

lint: ## Run linter
	docker compose exec api uv run ruff check .

format: ## Auto-format code
	docker compose exec api uv run ruff format .

seed: ## Re-run the database seed script
	docker compose exec -T postgres psql -U postgres -d intelligence_connector < scripts/seed.sql
