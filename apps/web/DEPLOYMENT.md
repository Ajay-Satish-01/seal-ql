# Deploying to Vercel

The documentation site (`apps/web`) depends on the local TypeScript SDK at `sdks/typescript` (`link:../../sdks/typescript`). Vercel must see the full repository and compile `dist/` before `next build`.

## Vercel project settings

1. **Import** the `seal` GitHub repository.
2. **Root Directory**: `apps/web` (Next.js auto-detected).
3. **Include source files outside of the Root Directory**: enable this in Root Directory settings so `../../sdks/typescript` is available during install/build.
4. **Node.js version**: 24 (from `apps/web/.nvmrc` / `engines` in `package.json`).
5. **Install Command**: `pnpm install --frozen-lockfile` (default; see `vercel.json`).
6. **Build Command**: `pnpm run build` — runs `build:sdk` (TypeScript SDK) then `next build`.

## What `pnpm build` does

```bash
# 1. Install + compile seal → sdks/typescript/dist/
pnpm --dir ../../sdks/typescript install --frozen-lockfile
pnpm --dir ../../sdks/typescript run build

# 2. Next.js production build
next build
```

`dist/` is gitignored; Vercel always builds it on deploy. Do not skip the SDK build step.

## Environment variables

Optional frontend env vars can be added in the Vercel dashboard. The demo uses static fixtures; no API URL is required for the docs site alone.

## Custom domain

After deploy, map a domain under **Project → Settings → Domains**.
