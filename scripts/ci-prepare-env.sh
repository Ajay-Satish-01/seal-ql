#!/usr/bin/env bash
# Create .env for docker compose when missing (CI has no committed .env).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example (compose / CI)"
fi
