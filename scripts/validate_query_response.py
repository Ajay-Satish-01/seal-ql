#!/usr/bin/env python3
"""Validate a live POST /v1/query response against QueryResponse shape."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

from response_validation import validate_query_response


def _print_summary(data: dict) -> None:
    chart = data.get("chart")
    chart_type = chart.get("chart_type") if isinstance(chart, dict) else None
    print("OK — response matches expected QueryResponse shape")
    print(f"  sql length: {len(data.get('sql', ''))}")
    columns = data.get("columns") or []
    print(f"  columns: {[c['name'] for c in columns if isinstance(c, dict)]}")
    print(f"  rows: {len(data.get('results') or [])}")
    print(f"  chart_type: {chart_type}")
    if isinstance(chart, dict) and chart_type in {"bar", "line", "scatter", "area", "pie"}:
        enc = (chart.get("vega_lite_spec") or {}).get("encoding", {})
        print(f"  encoding keys: {list(enc.keys())}")
    meta = data.get("metadata")
    if isinstance(meta, dict):
        print(f"  metadata keys: {list(meta.keys())}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "base_url",
        nargs="?",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="Show total revenue by product category",
        help="Natural language query",
    )
    args = parser.parse_args()

    url = f"{args.base_url.rstrip('/')}/v1/query"
    body = json.dumps({"query": args.query, "database_id": "default"}).encode()

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        print(f"HTTP {e.code}: {err_body[:500]}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return 1

    errors = validate_query_response(data)
    if errors:
        print("INCOMPATIBLE with QueryResponse / demo fixtures:")
        for err in errors:
            print(f"  - {err}")
        return 1

    _print_summary(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
