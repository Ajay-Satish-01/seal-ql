#!/usr/bin/env python3
"""Fail CI when package manifests drift from config/dependency-catalog.yaml."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "config" / "dependency-catalog.yaml"
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"

RESERVED_JS_KEYS = {"packages"}
RESERVED_PY_KEYS = {"packages", "constraints"}


def _load_catalog() -> dict[str, Any]:
    with CATALOG_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ── JavaScript helpers ─────────────────────────────────────────────────────────


def _satisfies_range(actual: str, catalog_range: str) -> bool:
    """True when *actual* is compatible with *catalog_range*.

    - Exact match always passes.
    - An exact pin (e.g. ``6.2.0``) satisfies a caret range with the same
      major (e.g. ``^6.2.0``).
    """
    if actual == catalog_range:
        return True
    m_cat = re.fullmatch(r"\^(\d+)\.\d+\.\d+", catalog_range)
    m_act = re.fullmatch(r"(\d+)\.\d+\.\d+", actual)
    return bool(m_cat and m_act and m_cat.group(1) == m_act.group(1))


def _verify_javascript(catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    js = catalog["javascript"]

    versions: dict[str, str] = {
        k: v for k, v in js.items() if k not in RESERVED_JS_KEYS and isinstance(v, str)
    }
    packages: dict[str, dict[str, list[str]]] = js["packages"]

    for rel_path, fields in packages.items():
        pkg_path = REPO_ROOT / rel_path / "package.json"
        with pkg_path.open(encoding="utf-8") as fh:
            manifest = json.load(fh)

        for field, dep_names in fields.items():
            section = manifest.get(field, {})
            for dep in dep_names:
                expected = versions.get(dep)
                if expected is None:
                    errors.append(
                        f"{rel_path}/package.json: dep {dep!r} listed under "
                        f"{field} but has no version in catalog"
                    )
                    continue
                actual = section.get(dep)
                if actual is None:
                    errors.append(
                        f"{rel_path}/package.json [{field}] {dep}: missing (expected {expected!r})"
                    )
                elif not _satisfies_range(actual, expected):
                    errors.append(
                        f"{rel_path}/package.json [{field}] {dep}: "
                        f"{actual!r} does not satisfy catalog {expected!r}"
                    )
    return errors


# ── Python helpers ─────────────────────────────────────────────────────────────


def _parse_toml_list_block(content: str, key: str) -> list[str]:
    """Extract quoted strings from a TOML inline list: ``key = ["a", "b"]``."""
    pattern = rf"^\s*{re.escape(key)}\s*=\s*\[(.*?)\]"
    match = re.search(pattern, content, flags=re.MULTILINE | re.DOTALL)
    if not match:
        return []
    return re.findall(r'"([^"]+)"', match.group(1))


def _parse_pyproject_dependency(path: Path, name: str) -> str | None:
    """Return the version suffix for *name* anywhere in a pyproject.toml."""
    content = path.read_text(encoding="utf-8")
    match = re.search(
        rf'^\s*"{re.escape(name)}([^"]*)"\s*,?\s*$',
        content,
        flags=re.MULTILINE,
    )
    return match.group(1) if match else None


_OPTIONAL_DEP_ALIASES: dict[str, str] = {
    "chromadb_linux_extra": "chromadb>=0.6,<0.7; sys_platform == 'linux'",
    "polars_optional": "polars>=1.15.0",
    "pandas_optional": "pandas>=2.2.0",
}


def _verify_python(catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    py = catalog["python"]

    # 1. Canonical dep versions (all keys that aren't reserved)
    versions: dict[str, str] = {
        k: v for k, v in py.items() if k not in RESERVED_PY_KEYS and isinstance(v, str)
    }

    # 2. Root constraint-dependencies
    constraints: dict[str, str] = py.get("constraints", {})
    root_content = ROOT_PYPROJECT.read_text(encoding="utf-8")
    for name, expected in constraints.items():
        entries = _parse_toml_list_block(root_content, "constraint-dependencies")
        needle = f"{name}{expected}"
        normalized = [e.replace(" ", "") for e in entries]
        if needle.replace(" ", "") not in normalized:
            errors.append(
                "pyproject.toml [tool.uv].constraint-dependencies: "
                f"missing or mismatched {name}{expected!r} "
                f"(found {entries!r})"
            )

    # 3. Per-package checks
    packages: dict[str, dict[str, Any]] = py.get("packages", {})
    for rel_path, spec in packages.items():
        pyproject_path = REPO_ROOT / rel_path / "pyproject.toml"
        content = pyproject_path.read_text(encoding="utf-8")

        for section_key, dep_list in spec.items():
            # Special optional-dep entries (e.g. chromadb_linux_extra)
            if section_key in _OPTIONAL_DEP_ALIASES:
                needle = _OPTIONAL_DEP_ALIASES[section_key]
                if needle not in content:
                    errors.append(
                        f"{rel_path}/pyproject.toml: missing optional extra entry {needle!r}"
                    )
                continue

            # section_key is 'dependencies' or 'dev' — dep_list is a list of names
            if not isinstance(dep_list, list):
                continue

            for dep_name in dep_list:
                expected = versions.get(dep_name) or constraints.get(dep_name)
                if expected is None:
                    errors.append(
                        f"{rel_path}/pyproject.toml: dep {dep_name!r} listed "
                        f"under {section_key} but has no version in catalog"
                    )
                    continue
                actual = _parse_pyproject_dependency(pyproject_path, dep_name)
                if actual is None:
                    errors.append(f"{rel_path}/pyproject.toml: missing dependency {dep_name!r}")
                    continue
                if actual != expected:
                    errors.append(
                        f"{rel_path}/pyproject.toml [{section_key}] {dep_name}: "
                        f"expected {dep_name}{expected!r}, "
                        f"got {dep_name}{actual!r}"
                    )
    return errors


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> int:
    if not CATALOG_PATH.is_file():
        print(f"❌ Missing catalog: {CATALOG_PATH}", file=sys.stderr)
        return 1

    catalog = _load_catalog()
    errors = _verify_javascript(catalog) + _verify_python(catalog)
    if errors:
        print("❌ Dependency catalog drift detected:\n", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        print(
            f"\nUpdate {CATALOG_PATH.relative_to(REPO_ROOT)} "
            "and matching manifests, then re-run make verify-dependency-catalog.",
            file=sys.stderr,
        )
        return 1

    print(f"✅ All manifests match {CATALOG_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
