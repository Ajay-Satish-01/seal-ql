#!/usr/bin/env bash
# Wait until the Ollama model from LLM_MODEL is pulled and loadable (CI E2E).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "${OLLAMA_PROFILE:-default}" == "disabled" ]]; then
  echo "OLLAMA_PROFILE=disabled — skipping Ollama wait"
  exit 0
fi

RAW_MODEL="${LLM_MODEL:-ollama/llama3.2:1b}"
MODEL="${RAW_MODEL#ollama/}"

echo "Waiting for Ollama model: ${MODEL} (from LLM_MODEL=${RAW_MODEL})"

for i in $(seq 1 90); do
  if docker compose exec -T ollama ollama show "${MODEL}" >/dev/null 2>&1; then
    echo "Ollama model ${MODEL} is available"
    exit 0
  fi
  echo "Waiting for Ollama model... (${i}/90)"
  sleep 10
done

echo "Ollama model ${MODEL} was not ready in time"
docker compose logs ollama --tail 80 || true
exit 1
