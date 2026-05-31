# Seal docs site (`apps/docs`)

Marketing, static documentation, and fixture-based interactive demo (`/demo`). Runs on port **3000**.

For the live API console (Query, Chat, Catalog, Settings, Vector), use **`apps/web`** on port **3001**.

## Doc routes

| Path | Topic |
| ---- | ----- |
| `/docs/how-it-works` | Guardrails, LLM stages, query vs chat pipeline |
| `/docs/configuration` | Environment reference with “what to expect” |
| `/docs/architecture` | System diagram and deployment topology |
| `/docs/chat-qa` | Chat overview |
| `/docs/data-catalog` | Global YAML catalog sync |
| `/docs/prompt-enhancement` | Enhancer chain |
| `/docs/guardrails` | Scope gate / abuse protection |
| `/docs/workspace` | Postgres workspace settings |
| `/docs/vector-rag` | Chroma / custom vector stores |
| `/docs/chat-streaming` | SSE (`seal.meta`, tokens) |
| `/docs/testing` | CI and local test commands |
| `/docs/agent-frameworks` | `seal-tools.openai.json` |

Contributor markdown mirrors: `docs/how-seal-works.md`, `docs/guardrails.md`, `docs/chat-enhancement.md`, etc.

Public assets: `/seal-tools.openai.json`, `/config/catalog.example.yaml` (synced via `make sync-docs-assets`).

## Development

```bash
# From repo root
make up          # API :8000
make sync-docs-assets

cd apps/docs
pnpm install
pnpm dev         # http://localhost:3000
```

The `/demo` route imports the linked TypeScript SDK (`seal`) for `VegaChart`. `next.config.ts` sets `turbopack.root` to the monorepo root in dev so the symlink resolves; see **Contributing** on the docs site.

## Build

```bash
make check-docs
# or
cd sdks/typescript && pnpm build
cd apps/docs && pnpm build
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for Vercel deployment.
