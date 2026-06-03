"""HTTP mapping for chat session store errors."""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

from fastapi import HTTPException

if TYPE_CHECKING:
    from seal_core.chat.session.ids import InvalidSessionIdError


def raise_session_not_found(exc: InvalidSessionIdError) -> NoReturn:
    raise HTTPException(status_code=404, detail="session_not_found") from exc
