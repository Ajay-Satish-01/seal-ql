from fastapi import APIRouter, Depends, Query, Security
from seal_core.database.registry import DatabaseRegistry
from seal_core.schema.models import DatabaseSchema

from app.database_routing import get_database_bundle
from app.dependencies import get_database_registry
from app.openapi_responses import AUTH_AND_DATABASE_RESPONSES
from app.security import require_api_key

router = APIRouter()


@router.get("/schema", response_model=DatabaseSchema, responses=AUTH_AND_DATABASE_RESPONSES)
async def get_schema(
    database_id: str = Query(
        "default",
        min_length=1,
        description="Target database identifier.",
    ),
    _: None = Security(require_api_key),
    registry: DatabaseRegistry = Depends(get_database_registry),  # noqa: B008
) -> DatabaseSchema:
    """Introspect and return the full database schema."""
    bundle = get_database_bundle(registry, database_id)
    schema = await bundle.introspector.introspect()
    return schema
