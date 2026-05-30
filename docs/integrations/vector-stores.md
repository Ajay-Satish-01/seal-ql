# Vector stores

`VECTOR_STORE` selects the implementation:

| Value | Behavior |
| ----- | -------- |
| `none` (default) | No vector RAG |
| `chroma` | Reference Chroma store — requires `chromadb` (see below) |

**Docker / `make up`:** set `VECTOR_STORE=chroma` in `.env`. `make up` passes `SEAL_EXTRA=chroma` to the API image build automatically (or set `SEAL_EXTRA=chroma` explicitly). Rebuild after changing: `docker compose build api`.

**Local (uv):** `uv sync --package seal-core --extra chroma` (Linux; macOS may need Docker for Chroma due to `onnxruntime` wheels).

**Production image:** `make docker-build SEAL_EXTRA=chroma`.
| Custom | `VECTOR_STORE_CLASS=your.module.Store` |

Index content includes catalog descriptions, schema comments, and optional files under `RAG_DOCUMENTS_PATH`.
