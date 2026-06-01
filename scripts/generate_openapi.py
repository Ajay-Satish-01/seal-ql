"""Script to generate the OpenAPI JSON specification."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic import BaseModel

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "apps" / "api"))

# Force deterministic generation regardless of the ambient shell environment:
# include documented routes and avoid production-only doc hiding.
os.environ["SEAL_DISABLE_DOCS"] = "false"
os.environ["SEAL_AUTH_REQUIRED"] = "false"
os.environ["SEAL_DEV_MODE"] = "true"

import yaml  # noqa: E402
from seal_core.settings import _load_settings  # noqa: E402

_load_settings.cache_clear()

from app.main import create_app  # noqa: E402
from app.schemas import (  # noqa: E402
    ChatMetadata,
    ChatResponse,
    ChatStreamMeta,
    EnhancementInfo,
    QueryOutOfScopeDetail,
    QueryOutOfScopeErrorResponse,
)


def _write_text(path: Path, content: str) -> None:
    """Write with exactly one trailing newline (matches pre-commit end-of-file-fixer)."""
    path.write_text(content.rstrip("\n") + "\n", encoding="utf-8")


def _inject_component_schemas(
    openapi_schema: dict[str, Any], models: list[type[BaseModel]]
) -> None:
    """Register Pydantic models used only in manual ``responses`` (e.g. SSE meta)."""
    schemas = openapi_schema.setdefault("components", {}).setdefault("schemas", {})
    for model in models:
        name = model.__name__
        if name in schemas:
            continue
        json_schema = model.model_json_schema(
            ref_template="#/components/schemas/{model}",
            mode="serialization",
        )
        nested_defs = json_schema.pop("$defs", None) or {}
        for def_name, def_schema in nested_defs.items():
            schemas.setdefault(def_name, def_schema)
        schemas[name] = json_schema


def generate() -> None:
    application = create_app()
    openapi_schema = application.openapi()
    _inject_component_schemas(
        openapi_schema,
        [
            ChatResponse,
            ChatStreamMeta,
            ChatMetadata,
            EnhancementInfo,
            QueryOutOfScopeDetail,
            QueryOutOfScopeErrorResponse,
        ],
    )

    output_json_path = root_dir / "apps" / "api" / "openapi.json"
    output_yaml_path = root_dir / "apps" / "api" / "openapi.yaml"

    _write_text(output_json_path, json.dumps(openapi_schema, indent=2))
    _write_text(
        output_yaml_path,
        yaml.dump(openapi_schema, default_flow_style=False, sort_keys=False),
    )

    print(f"✅ Generated OpenAPI JSON spec at {output_json_path}")
    print(f"✅ Generated OpenAPI YAML spec at {output_yaml_path}")


if __name__ == "__main__":
    generate()
