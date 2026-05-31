import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Security
from seal_core.catalog import sync_catalog
from seal_core.catalog.registry import DataCatalogRegistry
from seal_core.settings import get_settings
from seal_core.workspace.bootstrap import apply_catalog_overrides_to_registry

from app.dependencies import get_data_catalog, get_schema_introspector, get_workspace_store
from app.openapi_responses import UNAUTHORIZED_RESPONSE
from app.schemas import (
    CatalogDescriptionsPatch,
    CatalogResponse,
    CatalogSyncResponse,
)
from app.security import require_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/catalog", response_model=CatalogResponse, responses=UNAUTHORIZED_RESPONSE)
async def get_catalog(
    _: None = Security(require_api_key),
    registry: DataCatalogRegistry = Depends(get_data_catalog),  # noqa: B008
):
    """Return the loaded global data catalog."""
    cat = registry.catalog
    return CatalogResponse(
        version=cat.version,
        generated_at=cat.generated_at,
        schema_hash=cat.schema_hash,
        tables=[t.model_dump(by_alias=True) for t in cat.tables],
    )


@router.post("/catalog/sync", response_model=CatalogSyncResponse, responses=UNAUTHORIZED_RESPONSE)
async def sync_catalog_route(
    _: None = Security(require_api_key),
    introspector=Depends(get_schema_introspector),  # noqa: B008
    registry: DataCatalogRegistry = Depends(get_data_catalog),  # noqa: B008
    store=Depends(get_workspace_store),  # noqa: B008
):
    """Re-sync catalog YAML from live database schema."""
    settings = get_settings()
    if not settings.data_catalog_path:
        raise HTTPException(status_code=400, detail="DATA_CATALOG_PATH is not configured.")

    schema = await introspector.introspect()
    result = await sync_catalog(
        schema,
        Path(settings.data_catalog_path),
        prune_removed=settings.catalog_prune_removed,
    )
    registry.load(settings.data_catalog_path)
    overrides = await store.get_catalog_overrides()
    if overrides:
        apply_catalog_overrides_to_registry(registry, overrides)
    return CatalogSyncResponse(
        added=result.added,
        updated=result.updated,
        preserved=result.preserved,
        removed=result.removed,
        path=result.path,
    )


@router.patch(
    "/catalog/descriptions",
    response_model=CatalogResponse,
    responses=UNAUTHORIZED_RESPONSE,
)
async def patch_catalog_descriptions(
    body: CatalogDescriptionsPatch,
    _: None = Security(require_api_key),
    registry: DataCatalogRegistry = Depends(get_data_catalog),  # noqa: B008
    store=Depends(get_workspace_store),  # noqa: B008
):
    """Persist table/view description overrides to workspace DB (YAML may regenerate on sync)."""
    overrides = await store.get_catalog_overrides()
    for item in body.tables:
        key = f"{item.schema_name}.{item.name}"
        overrides[key] = {
            "table_description": item.table_description,
            "view_description": item.view_description,
        }
    await store.save_catalog_overrides(overrides)

    for item in body.tables:
        entry = registry.get_entry(item.name, item.schema_name)
        if entry is None:
            continue
        if item.table_description is not None:
            entry.table_description = item.table_description
        if item.view_description is not None:
            entry.view_description = item.view_description

    cat = registry.catalog
    return CatalogResponse(
        version=cat.version,
        generated_at=cat.generated_at,
        schema_hash=cat.schema_hash,
        tables=[t.model_dump(by_alias=True) for t in cat.tables],
    )
