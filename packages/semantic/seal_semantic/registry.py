import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from seal_semantic.models import SemanticModel

logger = logging.getLogger(__name__)


class SemanticRegistry:
    """
    Registry for loading and accessing SemanticModels from YAML files.
    """

    def __init__(self, directory_path: str | Path | None = None) -> None:
        self.models: dict[str, SemanticModel] = {}
        if directory_path:
            self.load_directory(directory_path)

    def load_directory(self, directory_path: str | Path) -> None:
        """Loads all .yaml and .yml files from the specified directory."""
        path = Path(directory_path)
        if not path.is_dir():
            logger.warning(f"Semantic directory not found: {directory_path}")
            return

        for file_path in path.glob("*.y*ml"):
            if file_path.suffix in (".yaml", ".yml"):
                self.load_file(file_path)

    def load_file(self, file_path: str | Path) -> None:
        """Loads a single YAML file containing one or more semantic models."""
        path = Path(file_path)
        try:
            with open(path, encoding="utf-8") as f:
                content = yaml.safe_load(f)

            if not content:
                return

            # Handle both single model and list of models
            models_data = content if isinstance(content, list) else [content]

            for model_data in models_data:
                self._add_model(model_data)

        except Exception as e:
            logger.error(f"Failed to load semantic file {path}: {e}")

    def _add_model(self, data: dict[str, Any]) -> None:
        try:
            model = SemanticModel(**data)
            self.models[model.name] = model
            logger.info(f"Loaded semantic model: {model.name}")
        except ValidationError as e:
            logger.error(f"Validation error in semantic model '{data.get('name', 'Unknown')}': {e}")

    def get_model(self, name: str) -> SemanticModel | None:
        """Retrieve a specific semantic model by name."""
        return self.models.get(name)

    def get_context_string(self) -> str:
        """
        Formats the semantic registry into a string suitable for LLM injection.
        """
        if not self.models:
            return ""

        lines = ["\n## Semantic Layer Definitions\n"]
        for model in self.models.values():
            lines.append(f"### Model: {model.name} (Table: {model.table})")
            if model.description:
                lines.append(f"Description: {model.description}")

            lines.append("Metrics:")
            for m in model.metrics:
                dim_str = f" (Slicable by: {', '.join(m.dimensions)})" if m.dimensions else ""
                desc_str = f" - {m.description}" if m.description else ""
                lines.append(f"  - {m.name} [{m.type}]: {m.sql}{desc_str}{dim_str}")

            lines.append("Dimensions:")
            for d in model.dimensions:
                expr_str = f" (Expression: {d.expr})" if d.expr else ""
                desc_str = f" - {d.description}" if d.description else ""
                lines.append(f"  - {d.name} [{d.type}]{expr_str}{desc_str}")
            lines.append("")

        return "\n".join(lines)
