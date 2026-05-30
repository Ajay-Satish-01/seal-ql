# Seal Docs Site

Documentation, marketing landing, and interactive demo (`/demo`) for Seal.

## Doc routes (chat & Q&A)

| Path | Topic |
| ---- | ----- |
| `/docs/chat-qa` | Chat overview, batteries-included stack |
| `/docs/data-catalog` | Global YAML catalog sync |
| `/docs/prompt-enhancement` | Enhancer chain |
| `/docs/vector-rag` | Chroma / custom vector stores |
| `/docs/chat-streaming` | SSE (`seal.meta`, tokens) |
| `/docs/agent-frameworks` | `seal-tools.openai.json` |

Public assets: `/seal-tools.openai.json`, `/config/catalog.example.yaml` (synced via `make sync-docs-assets`).

## Development

```bash
# From repo root — regenerate OpenAPI, demo fixtures, seal-tools, catalog example
make sync-docs-assets

cd apps/web
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). The demo includes **live chat** when you set base URL + API key.

## Build

```bash
cd sdks/typescript && pnpm build
cd apps/web && pnpm build
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for Vercel deployment.
