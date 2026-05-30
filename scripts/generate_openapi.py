"""Script to generate the OpenAPI JSON specification."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "apps" / "api"))

# Stable generation: include documented routes and avoid production-only doc hiding.
os.environ.setdefault("SEAL_DISABLE_DOCS", "false")
os.environ.setdefault("SEAL_AUTH_REQUIRED", "false")
os.environ.setdefault("SEAL_DEV_MODE", "true")

import yaml  # noqa: E402
from seal_core.settings import get_settings  # noqa: E402

get_settings.cache_clear()

from app.main import create_app  # noqa: E402


def _write_text(path: Path, content: str) -> None:
    """Write with exactly one trailing newline (matches pre-commit end-of-file-fixer)."""
    path.write_text(content.rstrip("\n") + "\n", encoding="utf-8")


def generate() -> None:
    application = create_app()
    openapi_schema = application.openapi()

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
