# Seal Docs Site

Documentation, marketing landing, and interactive demo (`/demo`) for Seal.

## Development

```bash
# From repo root — regenerate OpenAPI, demo fixtures, and public assets
make sync-docs-assets

cd apps/web
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000).

## Build

```bash
cd sdks/typescript && pnpm build
cd apps/web && pnpm build
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for Vercel deployment.
