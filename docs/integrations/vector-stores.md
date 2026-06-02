# Vector stores

**Doc index:** [../README.md](../README.md) · **Embedders (RAG boundary):** [../embedding.md](../embedding.md)

`VECTOR_STORE` selects the implementation used by `VectorRagEnhancer` on `/v1/chat` (when in scope and `CHAT_ENHANCEMENT_ENABLED=true`).

| Value | Behavior |
| ----- | -------- |
| `none` (default) | No vector RAG; enhancer disabled |
| `chroma` | On-disk Chroma — requires `chromadb` in the API image |
| Custom | Set `VECTOR_STORE_CLASS=your.module.Store` (and optional `VECTOR_STORE_CONFIG`) |

## What to expect

- **`none`** — Chat works without embeddings; no `/v1/vector` index maintenance.
- **`chroma`** — After `POST /v1/vector/reindex`, decision/answer prompts may include retrieved catalog or document chunks (`RAG_TOP_K`). Changing `EMBEDDING_MODEL` requires reindex.
- **Custom** — Your store must implement the vector protocol in `seal_core.vector`; register via `VECTOR_STORE_CLASS`.

Index content includes catalog descriptions, schema comments, and optional files under `RAG_DOCUMENTS_PATH`.

## Docker / local setup

**Docker / `make up`:** set `VECTOR_STORE=chroma` in `.env`. `make up` can pass `SEAL_EXTRA=chroma` to the API image build (or set explicitly). Rebuild after changing: `docker compose build api`.

**Local (uv):** `uv sync --package seal-core --extra chroma` (Linux; macOS may need Docker for Chroma due to `onnxruntime` wheels).

**Production image:** `make docker-build SEAL_EXTRA=chroma`.

Mount a volume at `CHROMA_PERSIST_PATH` (default `/app/data/chroma`) so indexes survive restarts.

## Related env vars

| Variable | Default | Purpose |
|----------|---------|---------|
| `EMBEDDING_MODEL` | `text-embedding-3-small` | LiteLLM embedding id for index/search |
| `RAG_TOP_K` | `5` | Chunks appended per chat turn |
| `RAG_MAX_CONTEXT_TOKENS` | `1500` | Cap on injected RAG text |
| `RAG_DOCUMENTS_PATH` | (optional) | Extra files to index |

Hot-reload: `rag_top_k` via workspace; `vector_store` and `embedding_model` require API restart.

User-facing: `/docs/vector-rag` · Pipeline: [../how-seal-works.md](../how-seal-works.md).
