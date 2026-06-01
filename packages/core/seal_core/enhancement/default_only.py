"""Helpers for enhancers that only apply to the default database."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from seal_core.database.config import database_id_from_metadata, is_default_database_id

if TYPE_CHECKING:
    from seal_core.enhancement.context import EnhancementContext

logger = logging.getLogger(__name__)


def default_database_only(ctx: EnhancementContext, *, feature: str) -> bool:
    """Return False and log when the turn targets a non-default database_id."""
    db_id = database_id_from_metadata(ctx.metadata)
    if is_default_database_id(db_id):
        return True
    logger.warning(
        "%s skipped for database_id=%r (available for default database only)",
        feature,
        db_id,
    )
    return False
