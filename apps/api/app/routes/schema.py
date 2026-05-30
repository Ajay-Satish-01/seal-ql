from fastapi import APIRouter, Depends, Security
from seal_core.schema.introspector import SchemaIntrospector
from seal_core.schema.models import DatabaseSchema

from app.dependencies import get_schema_introspector
from app.openapi_responses import UNAUTHORIZED_RESPONSE
from app.security import require_api_key

router = APIRouter()


@router.get("/schema", response_model=DatabaseSchema, responses=UNAUTHORIZED_RESPONSE)
async def get_schema(
    _: None = Security(require_api_key),
    introspector: SchemaIntrospector = Depends(get_schema_introspector),  # noqa: B008
) -> DatabaseSchema:
    """Introspect and return the full database schema."""
    schema = await introspector.introspect()
    return schema
