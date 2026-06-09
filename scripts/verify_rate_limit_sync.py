#!/usr/bin/env python3
"""Fail CI when rate-limit config copies or generated Python SDK drift."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "config" / "rate_limit_markers.json"
JSON_COPIES = (
    REPO_ROOT / "packages" / "core" / "seal_core" / "llm" / "rate_limit_markers.json",
    REPO_ROOT / "sdks" / "python" / "seal" / "rate_limit_markers.json",
)
PYTHON_SDK_CHECK = REPO_ROOT / "scripts" / "rate-limit-python-sdk.mjs"


def _verify_json_copies() -> bool:
    if not SOURCE.is_file():
        print(f"Missing source file: {SOURCE.relative_to(REPO_ROOT)}", file=sys.stderr)
        return False

    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    failed = False
    for copy in JSON_COPIES:
        rel = copy.relative_to(REPO_ROOT)
        if not copy.is_file():
            print(f"Missing {rel} — run: node scripts/sync-sdk-meta-vendor.mjs", file=sys.stderr)
            failed = True
            continue
        if json.loads(copy.read_text(encoding="utf-8")) != source:
            print(f"Out of sync: {rel}", file=sys.stderr)
            failed = True
    return not failed


def _verify_generated_python_sdk() -> bool:
    if not PYTHON_SDK_CHECK.is_file():
        print(f"Missing {PYTHON_SDK_CHECK.relative_to(REPO_ROOT)}", file=sys.stderr)
        return False
    result = subprocess.run(
        ["node", str(PYTHON_SDK_CHECK), "--check"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if result.stdout.strip():
            print(result.stdout.strip(), file=sys.stderr)
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        return False
    if result.stdout.strip():
        print(result.stdout.strip())
    return True


def main() -> int:
    json_ok = _verify_json_copies()
    python_ok = _verify_generated_python_sdk()
    if json_ok and python_ok:
        print("✅ rate_limit markers and generated Python SDK are in sync")
        return 0

    print(
        "\nRate-limit sync is out of date. Run: node scripts/sync-sdk-meta-vendor.mjs",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
