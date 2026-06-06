"""Shared JSON serialization helpers for non-native types."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID


def json_default(obj: object) -> object:
    """Fallback serialiser for ``json.dumps`` handling DB-native types.

    Converts:
    * ``Decimal`` → ``float``
    * ``datetime`` / ``date`` / ``time`` → ISO-8601 string
    * ``timedelta`` → total seconds (float)
    * ``UUID`` → string
    * ``bytes`` / ``bytearray`` → hex string
    * ``set`` / ``frozenset`` → list
    """
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, timedelta):
        return obj.total_seconds()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, (bytes, bytearray)):
        return obj.hex()
    if isinstance(obj, (set, frozenset)):
        return list(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def safe_json_dumps(obj: Any, **kwargs: Any) -> str:
    """``json.dumps`` with ``json_default`` pre-wired."""
    return json.dumps(obj, default=json_default, **kwargs)
