"""Script to generate the OpenAPI JSON specification."""

import json
from pathlib import Path

from app.main import app


def generate():
    openapi_schema = app.openapi()

    # Define output path
    root_dir = Path(__file__).parent.parent
    output_path = root_dir / "apps" / "api" / "openapi.json"

    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"✅ Generated OpenAPI spec at {output_path}")


if __name__ == "__main__":
    generate()
