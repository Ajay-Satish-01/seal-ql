# ---- Base Stage ----
FROM python:3.11-slim AS base

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy workspace-level files (lockfile required for reproducible prod builds)
COPY pyproject.toml uv.lock ./

# Copy all workspace members (needed for uv to resolve the workspace)
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY packages/core/pyproject.toml packages/core/pyproject.toml
COPY packages/sql/pyproject.toml packages/sql/pyproject.toml
COPY packages/charts/pyproject.toml packages/charts/pyproject.toml
COPY packages/semantic/pyproject.toml packages/semantic/pyproject.toml
COPY sdks/python/pyproject.toml sdks/python/pyproject.toml
COPY evals/pyproject.toml evals/pyproject.toml

# ---- Dev Stage ----
FROM base AS dev

# Install dependencies (cached layer)
RUN uv sync --frozen --no-install-workspace --all-packages

# Copy source code
COPY . .

# Install workspace packages in editable mode
RUN uv sync --frozen --all-packages

RUN chmod +x /app/scripts/healthcheck.py

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "/app/scripts/healthcheck.py"]

CMD ["uv", "run", "uvicorn", "app.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# ---- Prod Stage ----
FROM base AS prod

LABEL org.opencontainers.image.source="https://github.com/seal/seal"
LABEL org.opencontainers.image.description="Seal API"
LABEL org.opencontainers.image.licenses="MIT"

# Install production dependencies only (frozen lockfile)
RUN uv sync --frozen --no-install-workspace --all-packages --no-dev

# Copy source code
COPY . .

# Install workspace packages (no dev deps)
RUN uv sync --frozen --all-packages --no-dev

RUN chmod +x /app/scripts/healthcheck.py

ENV PATH="/app/.venv/bin:$PATH"

# Create non-root user
RUN adduser --disabled-password --gecos '' apiuser && \
    chown -R apiuser:apiuser /app
USER apiuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "/app/scripts/healthcheck.py"]

# No --reload in production
CMD ["uv", "run", "uvicorn", "app.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8000"]
