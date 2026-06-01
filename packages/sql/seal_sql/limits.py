"""Sanitizer limit configuration — single source for env-backed defaults."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class _Unset(Enum):
    """Sentinel distinguishing 'not provided' from an explicit None."""

    TOKEN = 0


UNSET: _Unset = _Unset.TOKEN


@dataclass(frozen=True)
class SanitizerLimits:
    """Row, offset, and complexity limits for SQLSanitizer."""

    max_rows: int = 10_000
    max_joins: int = 10
    max_subquery_depth: int = 5
    max_offset: int | None = None

    def __post_init__(self) -> None:
        if self.max_rows < 1:
            raise ValueError(f"max_rows must be >= 1, got {self.max_rows}")
        if self.max_joins < 0:
            raise ValueError(f"max_joins must be >= 0, got {self.max_joins}")
        if self.max_subquery_depth < 0:
            raise ValueError(f"max_subquery_depth must be >= 0, got {self.max_subquery_depth}")
        if self.max_offset is not None and self.max_offset < 0:
            raise ValueError(f"max_offset must be >= 0, got {self.max_offset}")

    @classmethod
    def merge(
        cls,
        base: SanitizerLimits,
        *,
        max_rows: int | _Unset = UNSET,
        max_joins: int | _Unset = UNSET,
        max_subquery_depth: int | _Unset = UNSET,
        max_offset: int | None | _Unset = UNSET,
    ) -> SanitizerLimits:
        """Return a copy of ``base`` with provided field overrides.

        Use ``UNSET`` (or omit the kwarg) to keep the base value.
        Pass an explicit value to override. Only ``max_offset`` accepts ``None``
        (to clear it); the other fields require a positive integer.
        """
        return cls(
            max_rows=(base.max_rows if isinstance(max_rows, _Unset) else max_rows),
            max_joins=(base.max_joins if isinstance(max_joins, _Unset) else max_joins),
            max_subquery_depth=(
                base.max_subquery_depth
                if isinstance(max_subquery_depth, _Unset)
                else max_subquery_depth
            ),
            max_offset=(base.max_offset if isinstance(max_offset, _Unset) else max_offset),
        )

    @property
    def effective_max_offset(self) -> int:
        """OFFSET cap defaults to max_rows when not set explicitly."""
        return self.max_offset if self.max_offset is not None else self.max_rows

    @classmethod
    def from_settings(cls) -> SanitizerLimits:
        """Build limits from centralized Settings (env vars)."""
        from seal_core.settings import get_settings

        settings = get_settings()
        return cls(
            max_rows=settings.max_rows,
            max_joins=settings.max_joins,
            max_subquery_depth=settings.max_subquery_depth,
        )


# Backwards-compatible module-level defaults (match Settings defaults).
DEFAULT_MAX_ROWS = 10_000
DEFAULT_MAX_JOINS = 10
DEFAULT_MAX_SUBQUERY_DEPTH = 5
