from fastapi import APIRouter, Depends
from intelligence_core.schema.introspector import SchemaIntrospector
from intelligence_core.schema.models import DatabaseSchema

from app.dependencies import get_schema_introspector

router = APIRouter()


@router.get("/schema", response_model=DatabaseSchema)
async def get_schema(
    introspector: SchemaIntrospector = Depends(get_schema_introspector),  # noqa: B008
):
    """Introspect and return the full database schema."""
    schema = await introspector.introspect()
    return schema
