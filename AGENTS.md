# AGENTS.md

## Repository Structure

- `apps/api/`: FastAPI backend service
- `packages/core/`: Core Models, Introspection & Planner
- `packages/sql/`: Dialect Validators & AST Safety checkers
- `packages/charts/`: Vega-Lite Spec Generators
- `packages/semantic/`: Semantic metrics registries
- `sdks/python/`: Python SDK wrapper
- `sdks/typescript/`: TypeScript SDK wrapper
- `scripts/`: Database seed scripts (`seed.sql`)

## Architecture

- **API Gateway**: Serves HTTP/gRPC traffic, passes payload to Query Planner.
- **Query Planner**: Utilizes LiteLLM + Instructor + Ollama to generate SQL from natural language.
- **SQL Validator**: Strict zero-trust safety boundary using SQLGlot AST parsing.
- **Database Executor**: Optimally queries DuckDB or Postgres (TimescaleDB).
- **Chart Spec Generator**: Produces Vega-Lite visual schemas based on return data.

## Docker

- Make sure this is docker first since we will be building this and hosting it in dockerhub and people will download the image and use self host it and connect to it using our sdk
- This will have multiple services ( Postgres, Ollama, API, etc)

## SDKs

- People will connect to this using our sdk, so make sure the sdk is easy to use, we have sdk for python and typescript
- Think about the best way to structure the sdk, for e.g, does it make sense to have a connector class that the user will import and use, or should it be a more functional approach?
- We should have proper documentation for the sdk, we can use something like mkdocs to generate documentation from the sdk code
- It should support different LLM providers, like OpenAI, Anthropic, Google, Ollama, etc
- It should support different database providers, like Postgres, DuckDB for now.


## Conventions

- Python dependencies are strictly managed through `uv` workspaces.
- TypeScript SDK relies entirely on `pnpm`.
- Fast, safe SQL generation is prioritized over complex multi-turn logic in a single request.
- Pydantic models must be used for all LLM structured outputs (Instructor).

## Commands

- `make up`: Start all local Docker services (API, Postgres, Ollama).
- `make down`: Stop all Docker services.
- `make seed`: Inject mock analytics schema into the database.
- `uv sync --all-packages --all-extras`: Install/sync all Python workspace dependencies.
- `uv run pytest -v`: Run tests safely across all Python workspaces.
- `pre-commit run --all-files`: Enforce formatting/linting via ruff, prettier, eslint.
- `pnpm install`: Install TypeScript SDK dependencies.

## Workflows

- **Schema Definition**: Make changes to `packages/core/` introspection. Validate against TimescaleDB and DuckDB.
- **Agent Queries**: Route through the API gateway. Never execute LLM-generated SQL without passing through `packages/sql/` AST validation.
- **Visualization**: Chart specs must map identically to the columns emitted by the SQL execution.

## Generation Rules

- **Zero-Trust**: Any dynamically generated SQL *must* be parsed by SQLGlot.
- **No Destructive Operations**: `DROP`, `DELETE`, `TRUNCATE`, and unbounded `SELECT` are completely forbidden. Pagination `LIMIT` is always enforced.
- **Model Output**: Rely on `instructor` to guarantee structured responses from local Ollama instances.

## Testing

- API tests must spin up the mock `seed` database.
- SQL Safety tests should include attempts to execute SQL injection payloads to verify the AST parser catches them.
- All Python tests must run in the `uv` virtual environment.

## Release Process

- Verify pre-commit hooks pass locally.
- Run the full test suite (`make seed` followed by `uv run pytest`).
- Ensure TypeScript SDK builds via `pnpm build`.
- SDK versions must align with the API protocol schema versions.

## Invariants

- Never bypass the `packages/sql/` AST parser.
- Never use generic connection drivers outside of the optimized `Database Executor` patterns.
- Never hardcode the LLM provider; always rely on `LiteLLM` to support seamless routing.
