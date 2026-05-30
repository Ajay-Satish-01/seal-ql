import json
from pathlib import Path


def test_seal_tools_manifest_paths() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "config" / "seal-tools.openai.json").read_text())
    names = {t["function"]["name"] for t in manifest["tools"]}
    assert names == {"seal_get_schema", "seal_get_catalog", "seal_query", "seal_chat"}
    for tool in manifest["tools"]:
        assert "x-seal" in tool
        assert tool["x-seal"]["path"].startswith("/v1/")
