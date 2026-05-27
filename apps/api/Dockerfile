FROM python:3.11-slim AS base

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy workspace-level files
COPY pyproject.toml ./

# Copy all workspace members (needed for uv to resolve the workspace)
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY packages/core/pyproject.toml packages/core/pyproject.toml
COPY packages/sql/pyproject.toml packages/sql/pyproject.toml
COPY packages/charts/pyproject.toml packages/charts/pyproject.toml
COPY packages/semantic/pyproject.toml packages/semantic/pyproject.toml
COPY sdks/python/pyproject.toml sdks/python/pyproject.toml
COPY evals/pyproject.toml evals/pyproject.toml

# Install dependencies (cached layer)
RUN uv sync --frozen --no-install-workspace 2>/dev/null || uv sync --no-install-workspace

# Copy source code
COPY . .

# Install workspace packages in editable mode
RUN uv sync

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
