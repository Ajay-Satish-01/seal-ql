# Releasing Seal

Published artifacts per release:

| Artifact | Name / tag |
|----------|------------|
| Docker Hub | `seal/api:<version>` and `:latest` |
| PyPI | `seal` |
| npm | `seal` |

## Prerequisites

1. Bump versions in lockstep:
   - `sdks/python/pyproject.toml`
   - `sdks/typescript/package.json`
   - `apps/api/pyproject.toml`
2. If the API surface changed (`apps/api/app/schemas.py`, route models, or `scripts/generate_openapi.py` injections):
   - `make openapi-ts`
   - `make sync-docs-assets` when demo fixtures or docs copies need refresh
   - Commit `apps/api/openapi.{json,yaml}`, `apps/docs/src/data/openapi.json`, `apps/docs/public/openapi.json`, and `sdks/typescript/src/generated/openapi.ts`
   - `make verify-openapi-sync` must pass (also enforced in CI `python-lint` and `package-check`)
3. Run `make check` locally.
4. Configure GitHub repository secrets:

| Secret | Used for |
|--------|----------|
| `DOCKERHUB_USERNAME` | Docker Hub login |
| `DOCKERHUB_TOKEN` | Docker Hub push |
| `PYPI_API_TOKEN` | PyPI upload (`uv publish`) |
| `NPM_TOKEN` | npm publish |

Create the Docker Hub repository `seal/api` before the first push.

Production deployments must set `SEAL_API_KEY` and `SEAL_AUTH_REQUIRED=true`. See `SETUP.md`.

## Publish

```bash
git tag v0.1.0
git push origin v0.1.0
```

The [Release workflow](.github/workflows/release.yml) runs on `v*` tags and publishes all three artifacts.

## Manual publish (fallback)

```bash
export VERSION=0.1.0

# Docker
make docker-push VERSION=$VERSION

# PyPI
make sdk-python-build
uv tool run twine check --strict dist/seal-*
UV_PUBLISH_TOKEN=... uv publish --package seal

# npm
cd sdks/typescript && pnpm install --frozen-lockfile && pnpm build && pnpm publish --access public
```
