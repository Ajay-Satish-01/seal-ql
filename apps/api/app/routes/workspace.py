"""Workspace settings and catalog override routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Security
from pydantic import BaseModel, Field
from seal_core.settings import get_settings
from seal_core.workspace.settings_schema import settings_schema

from app.dependencies import get_workspace_store
from app.openapi_responses import UNAUTHORIZED_RESPONSE
from app.security import require_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


class WorkspaceStorageInfo(BaseModel):
    settings_read_source: str = Field(
        "env",
        description="Where settings overrides were read: postgres, file, or env only.",
    )
    catalog_read_source: str = Field(
        "env",
        description="Where catalog overrides were read: postgres, file, or env only.",
    )
    write_target: str = Field(
        "postgres",
        description="Where dashboard writes persist: postgres or file.",
    )


class WorkspaceSettingsResponse(BaseModel):
    model_config = {"populate_by_name": True}

    settings: dict[str, Any]
    setting_fields: list[dict[str, Any]] = Field(default_factory=list, serialization_alias="schema")
    hot_reload_applied: list[str] = Field(default_factory=list)
    pending_apply: list[str] = Field(default_factory=list)
    restart_required: list[str] = Field(default_factory=list)
    storage: WorkspaceStorageInfo | None = None


class WorkspaceSettingsPatch(BaseModel):
    settings: dict[str, Any]


class WorkspaceExportResponse(BaseModel):
    settings: dict[str, Any]
    catalog_overrides: dict[str, Any]


async def _storage_info(store: Any) -> WorkspaceStorageInfo:
    getter = getattr(store, "get_storage_info", None)
    if getter is None:
        return WorkspaceStorageInfo()
    return WorkspaceStorageInfo(**await getter())


def _storage_from_result(result: dict[str, Any]) -> WorkspaceStorageInfo | None:
    info = result.get("storage")
    return WorkspaceStorageInfo(**info) if info else None


@router.get(
    "/workspace/settings",
    response_model=WorkspaceSettingsResponse,
    responses=UNAUTHORIZED_RESPONSE,
)
async def get_workspace_settings(
    _: None = Security(require_api_key),
    store=Depends(get_workspace_store),  # noqa: B008
):
    effective = await store.load_effective_settings()
    return WorkspaceSettingsResponse(
        settings=effective,
        storage=await _storage_info(store),
        setting_fields=[
            {
                "key": f.key,
                "env_name": f.env_name,
                "hot_reload": f.hot_reload,
                "value_type": f.value_type,
                "description": f.description,
                "default": f.default,
                "secret": f.secret,
            }
            for f in settings_schema()
        ],
    )


@router.patch(
    "/workspace/settings",
    response_model=WorkspaceSettingsResponse,
    responses=UNAUTHORIZED_RESPONSE,
)
async def patch_workspace_settings(
    body: WorkspaceSettingsPatch,
    _: None = Security(require_api_key),
    store=Depends(get_workspace_store),  # noqa: B008
):
    try:
        result = await store.patch_settings(
            body.settings,
            apply_hot_reload=get_settings().dev_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WorkspaceSettingsResponse(
        settings=result["settings"],
        hot_reload_applied=result.get("hot_reload_applied", []),
        pending_apply=result.get("pending_apply", []),
        restart_required=result.get("restart_required", []),
        storage=_storage_from_result(result),
    )


@router.post(
    "/workspace/settings/apply",
    response_model=WorkspaceSettingsResponse,
    responses=UNAUTHORIZED_RESPONSE,
)
async def apply_workspace_settings(
    _: None = Security(require_api_key),
    store=Depends(get_workspace_store),  # noqa: B008
):
    """Apply persisted hot-reload settings to the running API (prod dashboard button)."""
    result = await store.apply_persisted_settings()
    return WorkspaceSettingsResponse(
        settings=result["settings"],
        hot_reload_applied=result.get("hot_reload_applied", []),
        pending_apply=result.get("pending_apply", []),
        restart_required=result.get("restart_required", []),
        storage=_storage_from_result(result),
    )


@router.get(
    "/workspace/export",
    response_model=WorkspaceExportResponse,
    responses=UNAUTHORIZED_RESPONSE,
)
async def export_workspace(
    _: None = Security(require_api_key),
    store=Depends(get_workspace_store),  # noqa: B008
):
    data = await store.export_all()
    return WorkspaceExportResponse(**data)
