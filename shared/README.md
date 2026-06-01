# Shared frontend modules

TypeScript modules consumed by `apps/docs` and `apps/web` via tsconfig path aliases (`@seal/*`).

| Module | Purpose |
|--------|---------|
| `stream-meta.ts` | Runtime validation for SSE `seal.meta` (`parseStreamMeta`, `tryParseStreamMeta`, `partialStreamMetaFromRaw`) |
| `metadata-contract.ts` | Execution metadata types (`ScopeSource`, enhancement reason unions), `STREAM_META_METADATA_KEYS`, `chatResponseToStreamMeta` |
| `metadata-summary.ts` | Badge labels for dashboard metadata panels |
| `chat-sse-events.ts` | `mapChatSseEvent` — shared SSE → chat stream event mapping (docs + web) |
| `api-error.ts` | `formatApiError` — structured FastAPI errors (`query_out_of_scope`, session mismatch) |

`STREAM_META_METADATA_KEYS` is defined once in `config/stream_meta_metadata_keys.json` and loaded by Python (`validate_metadata.py`) and TypeScript (`metadata-contract.ts`). Validation parity: `tests/fixtures/stream_meta_validation_matrix.json` (pytest + `scripts/verify_stream_meta_validation_parity.ts`).

HTTP JSON/SSE **wire types** for the TypeScript SDK come from OpenAPI (`make openapi-ts` → `sdks/typescript/src/generated/openapi.ts`), not from this folder. The SDK **vendors** this directory on `prebuild` for runtime SSE validation only.

Contributor docs: [docs/chat-metadata.md](../docs/chat-metadata.md). Regenerate OpenAPI after changing `apps/api/app/schemas.py`.
