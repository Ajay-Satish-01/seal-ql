#!/usr/bin/env python3
"""Container health probe for the Seal API."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

HEALTH_URL = "http://127.0.0.1:8000/health"
TIMEOUT_SECONDS = 4


def main() -> None:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=TIMEOUT_SECONDS) as response:
            if response.status != 200:
                sys.exit(1)
            body = json.loads(response.read().decode())
            if body.get("status") != "ok":
                sys.exit(1)
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        sys.exit(1)


if __name__ == "__main__":
    main()
