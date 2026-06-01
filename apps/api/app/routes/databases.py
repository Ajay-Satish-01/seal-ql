from fastapi import APIRouter, Depends, Security
from seal_core.database.config import DEFAULT_DATABASE_ID
from seal_core.database.registry import DatabaseRegistry

from app.dependencies import get_database_registry
from app.openapi_responses import UNAUTHORIZED_RESPONSE
from app.schemas import DatabaseInfo, DatabasesListResponse
from app.security import require_api_key

router = APIRouter()


@router.get(
    "/databases",
    response_model=DatabasesListResponse,
    responses=UNAUTHORIZED_RESPONSE,
)
async def list_databases(
    _: None = Security(require_api_key),
    registry: DatabaseRegistry = Depends(get_database_registry),  # noqa: B008
) -> DatabasesListResponse:
    """List registered database identifiers (for clients and the dashboard)."""
    databases = [
        DatabaseInfo(
            database_id=database_id,
            dialect=registry.get(database_id).dialect,
            is_default=database_id == DEFAULT_DATABASE_ID,
        )
        for database_id in registry.list_ids()
    ]
    return DatabasesListResponse(databases=databases)
