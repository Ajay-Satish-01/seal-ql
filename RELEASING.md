# Releasing Seal

Published artifacts per release:

| Artifact | Name / tag |
|----------|------------|
| Docker Hub | `seal/api:<version>` and `:latest` |
| PyPI | `seal` |
| npm | `seal` |

**Related:** [DEPLOYMENT.md](DEPLOYMENT.md) (production deploy) · [CONTRIBUTORS.md](CONTRIBUTORS.md) (dev workflow) · [docs/README.md](docs/README.md) (documentation index)

---

## Pre-release checklist

### 1. Version bump (lockstep)

Update the same version in:

| File | Package |
|------|---------|
| `sdks/python/pyproject.toml` | PyPI `seal` |
| `sdks/typescript/package.json` | npm `seal` |
| `apps/api/pyproject.toml` | Docker image label / API package |

### 2. API surface & SDK types

If `apps/api/app/schemas.py`, route models, or `scripts/generate_openapi.py` injections changed:

```bash
make openapi-ts
make sync-docs-assets    # when demo fixtures or public OpenAPI copies need refresh
make verify-openapi-sync
```

Commit together:

- `apps/api/openapi.json`, `apps/api/openapi.yaml`
- `apps/docs/src/data/openapi.json`, `apps/docs/public/openapi.json`
- `sdks/typescript/src/generated/openapi.ts`

Injected schemas include SSE-only types (e.g. `ChatStreamMeta`) and guardrails errors (e.g. `QueryOutOfScopeErrorResponse`). See [sdks/typescript/README.md](sdks/typescript/README.md).

### 3. Metadata contract (if response shapes changed)

When query/chat/SSE metadata fields change:

- `config/stream_meta_metadata_keys.json`
- `packages/core/seal_core/pipeline/validate_metadata.py`
- `tests/fixtures/chat_flatten_golden.json`, `tests/fixtures/stream_meta_validation_matrix.json`
- `shared/stream-meta.ts`, `shared/metadata-contract.ts` (and SDK vendor sync via `prebuild`)

See [docs/chat-metadata.md](docs/chat-metadata.md) and the **Execution metadata contract** section in [CONTRIBUTORS.md](CONTRIBUTORS.md).

### 4. Documentation (user-visible behavior)

Update contributor markdown **and** matching docs site pages when behavior changes:

| Feature area | Contributor | Docs site |
|--------------|-------------|-----------|
| Embedding / BFF | [docs/embedding.md](docs/embedding.md) | `/docs/embedding` |
| `database_id` | [docs/multi-database.md](docs/multi-database.md) | `/docs/multi-database` |
| Guardrails / suggestions | [docs/guardrails.md](docs/guardrails.md) | `/docs/guardrails` |
| Execution metadata | [docs/chat-metadata.md](docs/chat-metadata.md) | `/docs/execution-metadata` |

Also review when operators need new env vars:

- [DEPLOYMENT.md](DEPLOYMENT.md) — Docker, `SEAL_DATABASES_*`, auth, guardrails
- [SETUP.md](SETUP.md) — quick reference
- [README.md](README.md) — high-level feature list

```bash
make check-docs
make check-dashboard
```

### 5. Validation

```bash
make check          # lint, unit tests, metadata parity, OpenAPI sync, docs + dashboard builds
make check-e2e      # optional but recommended before major releases (`make up` + `make seed`)
```

### 6. GitHub secrets (first-time setup)

| Secret | Used for |
|--------|----------|
| `DOCKERHUB_USERNAME` | Docker Hub login |
| `DOCKERHUB_TOKEN` | Docker Hub push |
| `PYPI_API_TOKEN` | PyPI upload (`uv publish`) |
| `NPM_TOKEN` | npm publish |

Create the Docker Hub repository `seal/api` before the first push.

### 7. Evals

After `make up && make seed`, run `make eval` or `make eval-planner` locally. See [docs/local-evals.md](docs/local-evals.md) and **Local planner evals** in [CONTRIBUTORS.md](CONTRIBUTORS.md).

### 8. Production defaults (communicate in release notes)

Shippers should set:

- `SEAL_API_KEY` + `SEAL_AUTH_REQUIRED=true` + `SEAL_DEV_MODE=false` + `SEAL_DISABLE_DOCS=true`
- BFF pattern for browser clients — [docs/embedding.md](docs/embedding.md)
- Mount `./config:/app/config` for catalog and optional `databases.yaml`

---

## Publish

```bash
git tag v0.1.0
git push origin v0.1.0
```

The [Release workflow](.github/workflows/release.yml) runs on `v*` tags and publishes Docker, PyPI, and npm.

### Post-tag smoke test (recommended)

```bash
docker pull seal/api:<version>
# With compose + .env from DEPLOYMENT.md:
curl http://localhost:8000/health
curl -H "X-API-Key: $SEAL_API_KEY" http://localhost:8000/v1/databases
curl -s -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" -H "X-API-Key: $SEAL_API_KEY" \
  -d '{"query":"Count orders","database_id":"default"}'
```

---

## Manual publish (fallback)

```bash
export VERSION=0.1.0

# Docker (SEAL_EXTRA=chroma if image needs Chroma RAG)
make docker-push VERSION=$VERSION

# PyPI
make sdk-python-build
uv tool run twine check --strict dist/seal-*
UV_PUBLISH_TOKEN=... uv publish --package seal

# npm
cd sdks/typescript && pnpm install --frozen-lockfile && pnpm build && pnpm publish --access public
```

Dry-run npm pack: `make sdk-npm-pack`.
