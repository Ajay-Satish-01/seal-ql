#!/usr/bin/env bash
# Quick smoke test: health + catalog (requires API running on localhost:8000).
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
API_KEY="${SEAL_API_KEY:?Set SEAL_API_KEY in .env (openssl rand -hex 32)}"

echo "→ GET $BASE_URL/health"
health=$(curl -sf "$BASE_URL/health")
echo "  $health"

echo "→ GET $BASE_URL/v1/catalog"
resp=$(curl -sf "$BASE_URL/v1/catalog" -H "X-API-Key: $API_KEY")
count=$(echo "$resp" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('tables',[])))")
first=$(echo "$resp" | python3 -c "import sys,json; t=json.load(sys.stdin).get('tables') or []; print((t[0].get('schema','?')+'.'+t[0].get('name','?')) if t else 'NONE')")
echo "  tables: $count (first: $first)"

if [ "$count" -eq 0 ]; then
  echo "❌ catalog has no tables — run: make seed && make sync-catalog"
  exit 1
fi

echo "✅ smoke test passed"
